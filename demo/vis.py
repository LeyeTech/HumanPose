
"""Functions to visualize human poses"""

import numpy as np
import os
import cv2


# Color (B, G, R)
COLOR_R1 = (120, 2, 240)
COLOR_R2 = (120-50, 0, 240-50)

COLOR_F1 = (80, 80, 80)
COLOR_F2 = (30, 30, 30)

COLOR_G1 = (142, 209, 169)
COLOR_G2 = (142-50, 209-50, 169-50)
COLOR_G3 = (142-100, 209-100, 169-100)

COLOR_Y1 = (0, 255, 255)
COLOR_Y2 = (0, 255-50, 255-50)
COLOR_Y3 = (0, 255-100, 255-100)

COLOR_B1 = (240, 176, 0)
COLOR_B2 = (240-50, 176-50, 0)
COLOR_B3 = (240-100, 176-100, 0)

COLOR_P1 = (243, 176, 252)
COLOR_P2 = (243-50, 176-50, 252-50)
COLOR_P3 = (243-100, 176-100, 252-100)

BBOX_COLOR = (0, 200, 0)

KPS_SKELETONS_AICH = [
    # 关键点开始索引，关键点结束索引，骨骼颜色，线宽
    ( 0, 13, COLOR_Y3,  4),
    (13,  3, COLOR_G3,  4),
    (13, 12, COLOR_R1,  4),

    ( 6, 14, COLOR_B1,  4),
    ( 9, 14, COLOR_P1,  4),
    (13, 14, COLOR_R2,  4),

    # ( 9,  3, COLOR_P1,  4),
    (10,  9, COLOR_P2, 4),
    (11, 10, COLOR_P3, 4),

    # ( 6,  0, COLOR_B1,  4),
    ( 7,  6, COLOR_B2, 4),
    ( 8,  7, COLOR_B3, 4),

    ( 5,  4, COLOR_G1, 4),
    ( 4,  3, COLOR_G2, 4),

    ( 2,  1, COLOR_Y1, 4),
    ( 1,  0, COLOR_Y2, 4),
]

KPS_JOINTS_AICH = [
    # 半径，颜色，线宽
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
    (4, COLOR_F2, 2),
]


KPS_SKELETONS = KPS_SKELETONS_AICH
KPS_JOINTS = KPS_JOINTS_AICH
POSE_NPOINTS = len(KPS_JOINTS)

def drawText(img, text, x_offset, y_offset,
        font_face=cv2.FONT_HERSHEY_COMPLEX, font_size=1,
        color=(0, 250, 250), thickness=2, lineType=cv2.LINE_AA,
        bg=True, bg_color=(0, 0, 0), bg_thickness=3):
    # 绘制FPS背景(实现描边)
    if bg:
        cv2.putText(img, text, (x_offset, y_offset), font_face, font_size,
                bg_color, bg_thickness, lineType=lineType)
    # 绘制FPS前景
    cv2.putText(img, text, (x_offset, y_offset), font_face, font_size,
            color, thickness, lineType=lineType)
    return img


def drawBox(img, box, box_score=None, box_pixel=None, color=BBOX_COLOR,
        thickness=1, text_y_offset=15, text_color=BBOX_COLOR,
        text_size=0.6, text_thickness=1):
    xmin, ymin, xmax, ymax = box[:4]
    cv2.rectangle(img, (xmin, ymin), (xmax, ymax), color, thickness)
    if box_score is not None:
        score_str = "%.1f" % (box_score*100)
        # 描边
        outline_color = tuple([255 - x for x in text_color])
        cv2.putText(img, score_str, (xmin, ymin+text_y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, text_size, outline_color,
                text_thickness+2, lineType=cv2.LINE_AA)
        cv2.putText(img, score_str, (xmin, ymin+text_y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, text_size, text_color,
                text_thickness, lineType=cv2.LINE_AA)
    if box_pixel is not None:
        x, y = box_pixel
        cv2.circle(img, (x, y), 8, (0, 0, 255), 8)

def drawLandmark(img, landmark, radius=2, color=COLOR_R1, thickness=2,
        lineType=cv2.LINE_AA):
    for (x, y) in landmark:
        cv2.circle(img, (x, y), radius, color, thickness, lineType=lineType)


def drawKps(img, kps, thr=0.5):
    # Draw skeletons
    for (idx_s, idx_e, color, thickness) in KPS_SKELETONS:
        kp_s = kps[idx_s]
        kp_e = kps[idx_e]
        if kp_s[2] < thr or kp_e[2] < thr:
            continue
        cv2.line(img, (kp_s[0], kp_s[1]), (kp_e[0], kp_e[1]), color,
                thickness, lineType=cv2.LINE_AA)
    # Draw joints
    for i, (radius, color, thickness) in enumerate(KPS_JOINTS):
        kp = kps[i]
        if kp[2] < thr:
            continue
        cv2.circle(img, (kp[0], kp[1]), radius, color, thickness,
                lineType=cv2.LINE_AA)

def drawActions(img, actions, color, font_size=1, thickness=3, coord_offset=0,
        edge_distance=50):
    img_h, img_w = img.shape[:2]

    up_x = img_w / 2 + coord_offset
    up_y = edge_distance
    down_x = up_x
    down_y = img_h - edge_distance
    left_x = edge_distance
    left_y = img_h / 2 + coord_offset
    right_x = img_w - edge_distance
    right_y = left_y
    front_x = edge_distance
    front_y = img_h - edge_distance + coord_offset
    back_x = img_w - edge_distance
    back_y = edge_distance + coord_offset

    if actions[0]:
        cv2.putText(img, '|', (int(up_x), int(up_y)), cv2.FONT_HERSHEY_SIMPLEX,
                font_size, color, thickness, lineType=cv2.LINE_AA)
    if actions[1]:
        cv2.putText(img, '|', (int(down_x), int(down_y)), cv2.FONT_HERSHEY_SIMPLEX,
                font_size, color, thickness, lineType=cv2.LINE_AA)
    if actions[2]:
        cv2.putText(img, '-', (int(left_x), int(left_y)), cv2.FONT_HERSHEY_SIMPLEX,
                font_size, color, thickness, lineType=cv2.LINE_AA)
    if actions[3]:
        cv2.putText(img, '-', (int(right_x), int(right_y)), cv2.FONT_HERSHEY_SIMPLEX,
                font_size, color, thickness, lineType=cv2.LINE_AA)
    if actions[4]:
        cv2.putText(img, '/', (int(front_x), int(front_y)), cv2.FONT_HERSHEY_SIMPLEX,
                font_size, color, thickness, lineType=cv2.LINE_AA)
    if actions[5]:
        cv2.putText(img, '/', (int(back_x), int(back_y)), cv2.FONT_HERSHEY_SIMPLEX,
                font_size, color, thickness, lineType=cv2.LINE_AA)



def drawActions2(img, box, actions, color, font_size=1, thickness=3,
        coord_offset=0, edge_distance=50):
    ''' 在Box范围内绘制actions
    '''
    box_xmin, box_ymin, box_xmax, box_ymax = box[:4]
    box_w = box_xmax - box_xmin
    box_h = box_ymax - box_ymin

    up_x = box_xmin + box_w / 2 + coord_offset
    up_y = box_ymin + edge_distance
    down_x = up_x
    down_y = box_ymax - edge_distance
    left_x = box_xmin + edge_distance
    left_y = box_ymin + box_h / 2 + coord_offset
    right_x = box_xmax - edge_distance
    right_y = left_y
    front_x = box_xmin + edge_distance
    front_y = box_ymax - edge_distance + coord_offset
    back_x = box_xmax - edge_distance
    back_y = box_ymin + edge_distance + coord_offset

    color_b = tuple([255-x for x in color])

    def _drawText(text, x_offset, y_offset):
        drawText(img, text, int(x_offset), int(y_offset), font_size=font_size,
                color=color, thickness=thickness, bg_color=color_b,
                bg_thickness=thickness+2)

    draw_params = [
        ('|', up_x, up_y),
        ('|', down_x, down_y),
        ('--', left_x, left_y),
        ('--', right_x, right_y),
        ('/', front_x, front_y),
        ('/', back_x, back_y),
    ]
    for i, action in enumerate(actions):
        if not action:
            continue
        _drawText(*draw_params[i])
