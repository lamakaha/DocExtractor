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
