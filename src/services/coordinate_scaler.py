from typing import List, Tuple

class CoordinateScaler:
    """
    Utility to scale coordinates between Gemini's normalized [0, 1000] system
    and actual image pixel dimensions.
    """

    @staticmethod
    def normalize_to_pixel(bbox_normalized: List[int], img_width: int, img_height: int) -> List[int]:
        """
        Converts Gemini [ymin, xmin, ymax, xmax] (0-1000) to pixel coordinates.
        Returns [ymin, xmin, ymax, xmax] in pixels.
        """
        if len(bbox_normalized) != 4:
            raise ValueError("Bounding box must have exactly 4 coordinates [ymin, xmin, ymax, xmax]")

        ymin, xmin, ymax, xmax = bbox_normalized

        if any(c < 0 or c > 1000 for c in [ymin, xmin, ymax, xmax]):
            raise ValueError("Normalized coordinates must be between 0 and 1000")

        # Scaling: coordinate / 1000 * dimension
        pixel_ymin = int(ymin * img_height / 1000)
        pixel_xmin = int(xmin * img_width / 1000)
        pixel_ymax = int(ymax * img_height / 1000)
        pixel_xmax = int(xmax * img_width / 1000)

        # Ensure we don't exceed image boundaries due to rounding
        pixel_ymin = max(0, min(pixel_ymin, img_height))
        pixel_xmin = max(0, min(pixel_xmin, img_width))
        pixel_ymax = max(0, min(pixel_ymax, img_height))
        pixel_xmax = max(0, min(pixel_xmax, img_width))

        return [pixel_ymin, pixel_xmin, pixel_ymax, pixel_xmax]

    @staticmethod
    def pixel_to_normalize(bbox_pixels: List[int], img_width: int, img_height: int) -> List[int]:
        """
        Converts pixel coordinates [ymin, xmin, ymax, xmax] to Gemini's normalized [0, 1000] system.
        Returns [ymin, xmin, ymax, xmax] normalized.
        """
        if len(bbox_pixels) != 4:
            raise ValueError("Bounding box must have exactly 4 coordinates [ymin, xmin, ymax, xmax]")

        ymin, xmin, ymax, xmax = bbox_pixels

        # Scaling: coordinate / dimension * 1000
        norm_ymin = int(ymin / img_height * 1000)
        norm_xmin = int(xmin / img_width * 1000)
        norm_ymax = int(ymax / img_height * 1000)
        norm_xmax = int(xmax / img_width * 1000)

        # Bound within 0-1000
        norm_ymin = max(0, min(norm_ymin, 1000))
        norm_xmin = max(0, min(norm_xmin, 1000))
        norm_ymax = max(0, min(norm_ymax, 1000))
        norm_xmax = max(0, min(norm_xmax, 1000))

        return [norm_ymin, norm_xmin, norm_ymax, norm_xmax]

    @staticmethod
    def pixel_to_canvas(bbox_pixels: List[int], img_width: int, img_height: int, canvas_width: int) -> List[int]:        
        """
        Scales pixel coordinates [ymin, xmin, ymax, xmax] to canvas display size.
        Maintains aspect ratio based on canvas_width.
        Returns [ymin, xmin, ymax, xmax] in canvas units.
        """
        if len(bbox_pixels) != 4:
            raise ValueError("Bounding box must have exactly 4 coordinates [ymin, xmin, ymax, xmax]")

        scale_factor = canvas_width / img_width

        ymin, xmin, ymax, xmax = bbox_pixels

        canvas_ymin = int(ymin * scale_factor)
        canvas_xmin = int(xmin * scale_factor)
        canvas_ymax = int(ymax * scale_factor)
        canvas_xmax = int(xmax * scale_factor)

        return [canvas_ymin, canvas_xmin, canvas_ymax, canvas_xmax]

# Convenience exports as module-level functions
def normalize_to_pixel(bbox_normalized: List[int], img_width: int, img_height: int) -> List[int]:
    return CoordinateScaler.normalize_to_pixel(bbox_normalized, img_width, img_height)

def pixel_to_normalize(bbox_pixels: List[int], img_width: int, img_height: int) -> List[int]:
    return CoordinateScaler.pixel_to_normalize(bbox_pixels, img_width, img_height)

def pixel_to_canvas(bbox_pixels: List[int], img_width: int, img_height: int, canvas_width: int) -> List[int]:
    return CoordinateScaler.pixel_to_canvas(bbox_pixels, img_width, img_height, canvas_width)

def normalize_to_canvas(bbox_normalized: List[int], canvas_width: int, canvas_height: int) -> List[int]:
    """
    Converts Gemini [ymin, xmin, ymax, xmax] (0-1000) to canvas coordinates [left, top, width, height].
    """
    if not bbox_normalized or len(bbox_normalized) != 4:
        return [0, 0, 0, 0]
        
    ymin, xmin, ymax, xmax = bbox_normalized
    
    top = int(ymin * canvas_height / 1000)
    left = int(xmin * canvas_width / 1000)
    bottom = int(ymax * canvas_height / 1000)
    right = int(xmax * canvas_width / 1000)
    
    # [left, top, width, height]
    return [left, top, right - left, bottom - top]
