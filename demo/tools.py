#coding: utf-8

def IOU(box1, box2):
    i_xmin = max(box1[0], box2[0])
    i_xmax = min(box1[2], box2[2])
    i_ymin = max(box1[1], box2[1])
    i_ymax = min(box1[3], box2[3])

    i_w = i_xmax - i_xmin
    i_h = i_ymax - i_ymin
    if i_w <= 0 or i_h <= 0:
        return 0

    i_area = i_w * i_h
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])

    iou = i_area / (box1_area + box2_area - i_area)
    return iou