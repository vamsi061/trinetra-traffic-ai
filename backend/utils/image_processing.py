import cv2
import numpy as np


def enhance_brightness(image, alpha=1.2, beta=30):
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)


def enhance_contrast(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def reduce_noise(image, strength=10):
    return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)


def remove_shadows(image):
    rgb_planes = cv2.split(image)
    result_planes = []
    for plane in rgb_planes:
        dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        blurred = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(plane, blurred)
        result_planes.append(diff)
    return cv2.merge(result_planes)


def enhance_low_light(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    enhanced = cv2.merge([l, a, b])
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def deblur_motion(image, kernel_size=5):
    kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
    blurred = cv2.filter2D(image, -1, kernel)
    result = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)
    return result


def remove_haze(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(16, 16))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    result = cv2.addWeighted(result, 1.2, cv2.GaussianBlur(result, (0, 0), 3), -0.2, 0)
    return result


def enhance_image(image):
    if image is None:
        return None
    enhanced = enhance_low_light(image)
    enhanced = deblur_motion(enhanced)
    enhanced = remove_haze(enhanced)
    enhanced = enhance_contrast(enhanced)
    enhanced = reduce_noise(enhanced)
    enhanced = enhance_brightness(enhanced)
    enhanced = remove_shadows(enhanced)
    return enhanced


def preprocess_for_ocr(region):
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh
