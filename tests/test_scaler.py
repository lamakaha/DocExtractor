import pytest
from src.services.coordinate_scaler import CoordinateScaler

def test_normalize_to_pixel():
    scaler = CoordinateScaler()
    img_width, img_height = 2000, 3000
    
    # 50% scale
    bbox_norm = [500, 500, 750, 750]
    expected_pixel = [1500, 1000, 2250, 1500]
    assert scaler.normalize_to_pixel(bbox_norm, img_width, img_height) == expected_pixel
    
    # 0% and 100% scale
    bbox_norm = [0, 0, 1000, 1000]
    expected_pixel = [0, 0, 3000, 2000]
    assert scaler.normalize_to_pixel(bbox_norm, img_width, img_height) == expected_pixel

def test_pixel_to_normalize():
    scaler = CoordinateScaler()
    img_width, img_height = 2000, 3000
    
    # 50% scale
    bbox_pixel = [1500, 1000, 2250, 1500]
    expected_norm = [500, 500, 750, 750]
    assert scaler.pixel_to_normalize(bbox_pixel, img_width, img_height) == expected_norm

    # 0% and 100% scale
    bbox_pixel = [0, 0, 3000, 2000]
    expected_norm = [0, 0, 1000, 1000]
    assert scaler.pixel_to_normalize(bbox_pixel, img_width, img_height) == expected_norm

def test_coordinate_scaler_out_of_bounds():
    scaler = CoordinateScaler()
    img_width, img_height = 2000, 3000
    
    with pytest.raises(ValueError):
        scaler.normalize_to_pixel([-1, 0, 500, 500], img_width, img_height)
        
    with pytest.raises(ValueError):
        scaler.normalize_to_pixel([0, 0, 1001, 1000], img_width, img_height)

def test_rounding():
    scaler = CoordinateScaler()
    # Test that rounding doesn't exceed image dimensions
    img_width, img_height = 100, 100
    bbox_norm = [999, 999, 1000, 1000]
    # 999 * 100 / 1000 = 99.9 -> 99
    # 1000 * 100 / 1000 = 100
    assert scaler.normalize_to_pixel(bbox_norm, img_width, img_height) == [99, 99, 100, 100]
