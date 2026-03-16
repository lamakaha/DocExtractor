import streamlit as st
import json
from streamlit_drawable_canvas import st_canvas
import io
from PIL import Image
from pdf2image import convert_from_bytes
from src.models.triplets import Triplet, BoundingBox
from src.ui.db_utils import (
    get_package_by_id, 
    get_extractions_for_package, 
    get_files_for_package, 
    update_extraction, 
    update_package_status
)
from src.utils.logging_utils import log_package_event
from src.services.coordinate_scaler import normalize_to_canvas
from src.services.analytical_service import AnalyticalService
from src.services.export_service import ExcelExporter

@st.cache_data(show_spinner=False)
def get_pdf_page(content: bytes, page_index: int) -> Image.Image:
    """Helper to convert a specific PDF page to a PIL Image."""
    try:
        pages = convert_from_bytes(content)
        if page_index < len(pages):
            return pages[page_index]
        return pages[0]
    except Exception as e:
        # Fallback to a blank image or raise
        raise RuntimeError(f"PDF rendering failed: {str(e)}")

def get_confidence_color(confidence: float) -> str:
    """Returns color based on confidence: Green (>0.95), Yellow (0.70-0.95), Red (<0.70)."""
    if confidence > 0.95:
        return "green"
    elif confidence >= 0.70:
        return "orange"
    else:
        return "red"

def serialize_triplet(obj):
    """Custom JSON serializer for Triplet and BoundingBox objects."""
    if isinstance(obj, Triplet):
        return obj.model_dump()
    if isinstance(obj, BoundingBox):
        return obj.model_dump()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def show_reviewer(package_id: str):
    """
    Displays the side-by-side reviewer interface for a given package.
    """
    # Initialize session state for navigation
    if "extraction_index" not in st.session_state:
        st.session_state.extraction_index = 0
    if "active_page_number" not in st.session_state:
        st.session_state.active_page_number = 1

    package = get_package_by_id(package_id)
    if not package:
        st.error(f"Package {package_id} not found.")
        if st.button("Back to Dashboard"):
            st.session_state.current_view = "Dashboard"
            st.rerun()
        return

    extractions = get_extractions_for_package(package_id)
    if not extractions:
        st.warning("No extractions found for this package.")
        if st.button("Back to Dashboard"):
            st.session_state.current_view = "Dashboard"
            st.rerun()
        return

    # Ensure index is within bounds (in case it was set for another package)
    if st.session_state.extraction_index >= len(extractions):
        st.session_state.extraction_index = 0

    # Clear active_bbox if we changed extraction
    if "last_extraction_id" not in st.session_state or st.session_state.last_extraction_id != extractions[st.session_state.extraction_index].id:
        st.session_state.active_bbox = None
        st.session_state.active_page_number = 1
        st.session_state.last_extraction_id = extractions[st.session_state.extraction_index].id

    num_extractions = len(extractions)
    
    # Navigation and Title
    col_title, col_nav = st.columns([3, 1])
    with col_title:
        st.title(f"Review: {package.original_filename}")
    
    with col_nav:
        st.write("") # Spacer
        if num_extractions > 1:
            prev_col, next_col = st.columns(2)
            with prev_col:
                if st.button("←", disabled=st.session_state.extraction_index == 0, help="Previous Page"):
                    st.session_state.extraction_index -= 1
                    st.session_state.active_bbox = None
                    st.session_state.active_page_number = 1
                    st.rerun()
            with next_col:
                if st.button("→", disabled=st.session_state.extraction_index == num_extractions - 1, help="Next Page"):
                    st.session_state.extraction_index += 1
                    st.session_state.active_bbox = None
                    st.session_state.active_page_number = 1
                    st.rerun()
            st.write(f"Page {st.session_state.extraction_index + 1} of {num_extractions}")

    current_extraction = extractions[st.session_state.extraction_index]
    
    # Get the image file for this extraction
    image_file = None
    if current_extraction.file_id:
        files = get_files_for_package(package_id)
        image_file = next((f for f in files if f.id == current_extraction.file_id), None)
    
    if not image_file:
        files = get_files_for_package(package_id)
        image_file = next((f for f in files if f.mime_type and f.mime_type.startswith("image/")), None)

    # Side-by-Side Layout
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("Document View")
        if image_file and image_file.content:
            # Handle PDF to image conversion for display
            if image_file.mime_type == "application/pdf":
                try:
                    img = get_pdf_page(image_file.content, st.session_state.extraction_index)
                    if st.session_state.active_page_number > 1:
                        img = get_pdf_page(image_file.content, st.session_state.active_page_number - 1)
                except Exception as e:
                    st.error(f"Failed to render PDF: {e}")
                    return
            else:
                try:
                    img = Image.open(io.BytesIO(image_file.content))
                except Exception as e:
                    st.error(f"Failed to open image: {e}")
                    return
            
            img_width, img_height = img.size
            
            # Dynamic canvas width calculation
            canvas_width = 700 
            scale_factor = canvas_width / img_width
            canvas_height = int(img_height * scale_factor)

            # Check for active_bbox to highlight
            initial_drawing = None
            if st.session_state.get("active_bbox"):
                # active_bbox is [ymin, xmin, ymax, xmax] normalized 0-1000
                bbox_normalized = st.session_state.active_bbox
                # Use normalize_to_canvas to get display coordinates [left, top, width, height]
                left, top, width, height = normalize_to_canvas(bbox_normalized, canvas_width, canvas_height)
                
                initial_drawing = {
                    "version": "4.4.0",
                    "objects": [
                        {
                            "type": "rect",
                            "originX": "left",
                            "originY": "top",
                            "left": left,
                            "top": top,
                            "width": width,
                            "height": height,
                            "fill": "rgba(255, 165, 0, 0.3)",
                            "stroke": "#e00",
                            "strokeWidth": 2,
                        }
                    ]
                }

            # Render the document image using st_canvas
            st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=2,
                stroke_color="#e00",
                background_image=img,
                update_streamlit=True,
                height=canvas_height,
                width=canvas_width,
                drawing_mode="transform",
                display_toolbar=False,
                key=f"canvas_{current_extraction.id}",
                initial_drawing=initial_drawing,
            )
        else:
            st.error("No image found for this extraction.")

    with col_right:
        st.subheader("Extraction Details")
        st.write(f"**Document Type:** {current_extraction.document_type}")
        st.write(f"**Overall Confidence:** {current_extraction.confidence_score:.2f}")
        
        st.divider()

        # Parse extraction JSON
        try:
            extraction_data = json.loads(current_extraction.extraction_json)
        except Exception:
            extraction_data = {}

        # Tracking form values
        new_values = {}
        
        # We'll use a unique key for each input to ensure no collisions
        prefix = f"form_{current_extraction.id}_"

        for field_name, field_triplet in extraction_data.items():
            # Triplet could be a dict if coming from JSON
            if isinstance(field_triplet, dict):
                # Ensure it has the right keys for Pydantic
                triplet = Triplet(**field_triplet)
            else:
                triplet = field_triplet
            
            color = get_confidence_color(triplet.confidence)
            
            # Field Layout: Color indicator, label, value, locate button
            c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
            with c1:
                st.markdown(f'<div style="background-color:{color}; width:15px; height:15px; border-radius:50%; margin-top:35px;"></div>', unsafe_allow_html=True)
            with c2:
                new_val = st.text_input(
                    f"{field_name}", 
                    value=str(triplet.value), 
                    key=f"{prefix}{field_name}",
                    help=f"Confidence: {triplet.confidence:.2%}"
                )
                new_values[field_name] = new_val
            with c3:
                st.write("") # Spacer
                if triplet.bbox and st.button("🔍", key=f"locate_{current_extraction.id}_{field_name}", help="Locate on document"):
                    st.session_state.active_bbox = triplet.bbox.coordinates
                    if triplet.page_number:
                        st.session_state.active_page_number = triplet.page_number
                    st.rerun()

        st.divider()
        
        col_approve, col_back = st.columns(2)
        with col_approve:
            if st.button("Approve", type="primary", use_container_width=True):
                # Update extraction data with new values
                updated_data = extraction_data.copy()
                for field_name, new_val in new_values.items():
                    if isinstance(updated_data[field_name], dict):
                        updated_data[field_name]['value'] = new_val
                    else:
                        # If it was already a Triplet object, update its value
                        updated_data[field_name].value = new_val
                
                # Convert back to JSON for storage
                update_extraction(current_extraction.id, json.dumps(updated_data, default=serialize_triplet), is_reviewed=True)
                update_package_status(package_id, "APPROVED")
                log_package_event(package_id, "REVIEW", "Package manually approved by user", level="SUCCESS", new_status="APPROVED")
                
                st.toast("Extraction approved!")
                st.session_state.current_view = "Dashboard"
                st.rerun()

        with col_back:
            if st.button("Back to Dashboard", key="back_to_dashboard", use_container_width=True):
                st.session_state.current_view = "Dashboard"
                st.rerun()

        # Single Package Export
        if package.status == "APPROVED":
            st.divider()
            if st.button("Prepare Package Export", use_container_width=True):
                try:
                    analytical = AnalyticalService()
                    exporter = ExcelExporter()
                    
                    summary_df = analytical.get_summary()
                    transactions_df = analytical.get_transactions()
                    
                    # Filter dataframes for this package only
                    filtered_summary = summary_df[summary_df['package_id'] == package_id]
                    filtered_transactions = transactions_df[transactions_df['package_id'] == package_id]
                    
                    # Prepare data for export
                    summary_data = filtered_summary.rename(columns={'effective_date': 'document_date'}).to_dict('records')
                    transactions_data = filtered_transactions.to_dict('records')
                    
                    excel_stream = exporter.generate_excel(summary_data, transactions_data)
                    
                    st.download_button(
                        label="⬇️ Download Excel",
                        data=excel_stream,
                        file_name=f"export_{package.original_filename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
