import cv2
import numpy as np
import config


def get_expanded_motorcycle_bbox(motorcycle_bbox, img_shape=(None, None)):
    """Expand motorcycle bbox to capture riders sitting above and behind.

    Expansion factors:
      - left:   0.4 * width   (capture handlebar / rider lean)
      - right:  0.4 * width   (capture pillion / side passenger)
      - top:    0.6 * height  (capture rider's torso / head above seat)
      - bottom: 0.3 * height  (capture lower body / child in front)
    """
    x1, y1, x2, y2 = motorcycle_bbox
    w = x2 - x1
    h = y2 - y1
    if w <= 0 or h <= 0:
        return motorcycle_bbox

    ex1 = x1 - 0.4 * w
    ey1 = y1 - 0.6 * h
    ex2 = x2 + 0.4 * w
    ey2 = y2 + 0.3 * h

    h_img, w_img = img_shape[:2] if img_shape and img_shape[0] else (None, None)
    if h_img and w_img:
        ex1 = max(0, ex1)
        ey1 = max(0, ey1)
        ex2 = min(w_img, ex2)
        ey2 = min(h_img, ey2)

    return [ex1, ey1, ex2, ey2]


def is_person_on_motorcycle(person_bbox, motorcycle_bbox, img_shape=(None, None)):
    """Check if person center falls inside expanded motorcycle region."""
    cx = (person_bbox[0] + person_bbox[2]) / 2
    cy = (person_bbox[1] + person_bbox[3]) / 2
    ex1, ey1, ex2, ey2 = get_expanded_motorcycle_bbox(motorcycle_bbox, img_shape)
    return ex1 <= cx <= ex2 and ey1 <= cy <= ey2


def associate_riders(persons, motorcycles, img_shape=(None, None)):
    """For each motorcycle, return list of associated persons.

    Returns:
        List of dicts: {motorcycle, riders: [person, ...]}
    """
    results = []
    for mc in motorcycles:
        riders = []
        for p in persons:
            if is_person_on_motorcycle(p['bbox'], mc['bbox'], img_shape):
                riders.append(p)
        results.append({
            'motorcycle': mc,
            'riders': riders,
            'rider_count': len(riders),
        })
    return results


def person_in_car_expanded(person_bbox, car_bbox, img_shape=(None, None)):
    """Check if person center falls inside slightly expanded car region."""
    x1, y1, x2, y2 = car_bbox
    w = x2 - x1
    h = y2 - y1
    if w <= 0 or h <= 0:
        return False
    # Slight expansion for car (less than motorcycle since occupants are inside)
    ex1 = x1 - 0.1 * w
    ey1 = y1 - 0.1 * h
    ex2 = x2 + 0.1 * w
    ey2 = y2 + 0.1 * h
    cx = (person_bbox[0] + person_bbox[2]) / 2
    cy = (person_bbox[1] + person_bbox[3]) / 2
    return ex1 <= cx <= ex2 and ey1 <= cy <= ey2


def draw_debug_association(image, persons, motorcycles, associations):
    """Draw debug visualization: motorcycle bbox, expanded region, person bbox, riders.

    Saves to config.DATA_DIR / 'debug_association.jpg'
    """
    debug = image.copy()
    for assoc in associations:
        mc = assoc['motorcycle']
        riders = assoc['riders']
        mx1, my1, mx2, my2 = [int(v) for v in mc['bbox']]

        # Expanded region in yellow
        ex1, ey1, ex2, ey2 = get_expanded_motorcycle_bbox(mc['bbox'], image.shape[:2])
        cv2.rectangle(debug, (int(ex1), int(ey1)), (int(ex2), int(ey2)), (0, 255, 255), 2)

        # Motorcycle bbox in blue
        cv2.rectangle(debug, (mx1, my1), (mx2, my2), (255, 0, 0), 2)
        label = mc.get('instance_id', 'motorcycle')
        cv2.putText(debug, f"{label} ({assoc['rider_count']} riders)",
                    (mx1, my1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Riders in red
        for rider in riders:
            rx1, ry1, rx2, ry2 = [int(v) for v in rider['bbox']]
            cv2.rectangle(debug, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)
            rid = rider.get('instance_id', 'person')
            cv2.putText(debug, rid, (rx1, ry1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # Non-associated persons in green
    rider_person_ids = set()
    for assoc in associations:
        for r in assoc['riders']:
            rider_person_ids.add(id(r))
    for p in persons:
        if id(p) not in rider_person_ids:
            rx1, ry1, rx2, ry2 = [int(v) for v in p['bbox']]
            cv2.rectangle(debug, (rx1, ry1), (rx2, ry2), (0, 255, 0), 2)

    cv2.putText(debug, "DEBUG: Blue=MC Yellow=Expanded Red=Rider Green=Person",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    import os
    from datetime import datetime
    debug_path = os.path.join(config.DATA_DIR, f'debug_association_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')
    cv2.imwrite(debug_path, debug)
    return debug_path
