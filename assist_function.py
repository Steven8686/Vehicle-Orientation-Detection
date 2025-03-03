# Steven8686, Redem-cat YOLOv5-based vehicle orientation detect, AGPL-3.0 license
"""
Some assistant functions
"""
import numpy as np
import cv2
import os

def expand_and_crop(img, xyxy, scale_factor=1.1):
    """
    Crop tires from original image according to yolov5 detection
    Args:
        img (ndarray): original image.
        xyxy (tuple(int)): coords of cropping.
        scale_factor (float): scaling sub picture a little larger for more accurate detection. Default=1.1.
    Returns:
        cropped_img (ndarray): cropped image.
    """

    x1, y1, x2, y2 = xyxy

    original_width = x2 - x1
    original_height = y2 - y1

    # adjust w,h based on scaling factor
    expanded_width = int(original_width * scale_factor)
    expanded_height = int(original_height * scale_factor)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2  # 中心点
    half_expanded_width = expanded_width // 2
    half_expanded_height = expanded_height // 2

    # boundary safety
    new_x1 = max(cx - half_expanded_width, 0)
    new_y1 = max(cy - half_expanded_height, 0)
    new_x2 = min(cx + half_expanded_width, img.shape[1])
    new_y2 = min(cy + half_expanded_height, img.shape[0])

    cropped_img = img[new_y1:new_y2, new_x1:new_x2]
    return cropped_img


def is_rectangle_inside(inner_rect, outer_rect):
    """
    Check if a rect is fully contained in another rect
    Args:
        inner_rect (list):xyxy format of rect inside
        outer_rect (list):xyxy format of rect outside
    Return:
        if inner_rect is contained in outer_rect
    """

    return (inner_rect[0] >= outer_rect[0]
            and inner_rect[2] <= outer_rect[2]
            and inner_rect[1] >= outer_rect[1]
            and inner_rect[3] <= outer_rect[3])


def check_containment(rectangles, conf):
    """
    Check the containment relationship of all detected rectangles
    Tires should be fully contained in a vehicle rect to make sure it belongs to that vehicle
    Args:
        rectangles (list): all rectangles'
        conf (float): confidence. all rectangles below the given confidence will be ignored.
    Returns:
        contained_rects (list): elements stand for rects belong to one vehicle
    """
    inner_rects = []  # tires
    outer_rects = []  # vehicles

    for i, rect in enumerate(rectangles):
        if rect[4] < conf:  # ignore low conf rects
            rect.append(-1)
            continue
        if 0 <= rect[5] <= 3:  # class 0-3: tire
            rect.append(i)
            inner_rects.append(rect)
        elif rect[5] in [4, 5]:  # class 4-5: vehicle
            rect.append(i)
            outer_rects.append(rect)

    # following part seems time-consuming if too much rects are given
    # for vehicles with 2+ tires on one side, it gives a random connection among all the tires
    contained_rects = []
    for outer in outer_rects:
        c = [-1, -1, -1]
        for inner in inner_rects:
            if is_rectangle_inside(inner, outer):
                c[2] = outer[6]
                if inner[5] in [1, 2]:
                    c[0] = inner[6]
                else:
                    c[1] = inner[6]

        if c[0] != -1 and c[1] != -1 and c[2] != -1:
            contained_rects.append(c)

    return contained_rects


def paint_contour(image, contour):
    """
    Debug only, you may use this to paint contours.
    """
    h, w = image.shape[:2]
    points_2d = contour.squeeze(1)
    x_coords = points_2d[:, 0].astype(int)
    y_coords = points_2d[:, 1].astype(int)

    mask = np.zeros((w, h), dtype=bool)
    mask[x_coords, y_coords] = True
    mask = mask.T
    a = np.where(mask, 255, 0)
    j = 1
    while os.path.exists("./contours/contour"+str(j)+".jpg"):
        j += 1
    cv2.imwrite("./contours/contour"+str(j)+".jpg", a)


def interpolate_contour_gap(contour, max_gap=2):
    """
    Use linear interpolation to force contours close. Generated by deepseek.
    cv2.contourArea requires shape to be mostly closed, otherwise it gives wrong answer.
    Args:
        contour (ndarray): Input contour.
        max_gap (float): The maximum distance between current point and next point. If the distance is larger than
        max_gap, it will add extra points to connect.
    Return:
        new_contour (ndarray): Modified contour.
    """
    new_contour = []
    for i in range(len(contour)):
        pt1 = contour[i][0]
        pt2 = contour[(i+1) % len(contour)][0]
        distance = np.linalg.norm(pt2 - pt1)
        if distance > max_gap:
            # 在两个点之间插入中间点
            num_points = int(distance / max_gap) + 1
            x = np.linspace(pt1[0], pt2[0], num_points)
            y = np.linspace(pt1[1], pt2[1], num_points)
            for xi, yi in zip(x[:-1], y[:-1]):  # 避免重复添加终点
                new_contour.append([[xi, yi]])
        else:
            new_contour.append([pt1])
    return np.array(new_contour, dtype=np.int32)

