"""Illegal Parking Detection for TRINETRA AI.

Rules:
- Never flag a vehicle as illegally parked unless parking context evidence exists.
- Skip analysis if rider mounted + vehicle in active traffic lane (moving vehicle).
- Requires BOTH: stationary context AND blocking position.
"""

import logging
import config
logger = logging.getLogger(__name__)


def _has_parking_context(detections, image_shape):
    """Check if image contains parking-relevant context cues.
    
    Returns: (has_context: bool, context_clues: list[str])
    """
    h, w = image_shape[:2]
    clues = []

    vehicles = [d for d in detections if d['class_id'] in (2, 3, 5, 7)]
    persons = [d for d in detections if d['class_id'] == 0]

    for veh in vehicles:
        x1, y1, x2, y2 = veh['bbox']
        box_h = y2 - y1
        box_w = x2 - x1
        veh_cy = (y1 + y2) / 2
        cx = (x1 + x2) / 2

        # Vehicle occupies lower quarter of image with wide aspect → likely parked near curb
        if y1 > h * 0.75 and box_w > w * 0.3 and box_h < h * 0.25:
            clues.append('curb_side_parking')

        # Vehicle very close to image bottom edge → footpath/curb proximity
        if y2 >= h * 0.95 and box_h < h * 0.3:
            clues.append('footpath_proximity')

        # Vehicle in lower half with nearby pedestrians → possible roadside parking
        if veh_cy > h * 0.5:
            nearby_pedestrians = sum(
                1 for p in persons
                if abs((p['bbox'][1] + p['bbox'][3]) / 2 - veh_cy) < h * 0.25
            )
            if nearby_pedestrians >= 4:
                clues.append('roadside_parking_with_pedestrians')

        # Vehicle at extreme edge of frame → parked at roadside
        edge_margin = w * 0.05
        if (cx < edge_margin or cx > w - edge_margin) and box_h < h * 0.35:
            clues.append('edge_parked_vehicle')

    return len(clues) > 0, clues


def _is_mounted_rider(detections):
    """Check if any person appears mounted on a motorcycle (moving vehicle hint).
    
    Returns True if a person is likely riding a motorcycle.
    """
    persons = [d for d in detections if d['class_id'] == 0]
    motorcycles = [d for d in detections if d['class_id'] == 3]

    if not persons or not motorcycles:
        return False

    for mc in motorcycles:
        mx1, my1, mx2, my2 = mc['bbox']
        mc_cy = (my1 + my2) / 2
        mc_cx = (mx1 + mx2) / 2
        mc_w = mx2 - mx1
        mc_h = my2 - my1

        for p in persons:
            px1, py1, px2, py2 = p['bbox']
            p_cy = (py1 + py2) / 2
            p_cx = (px1 + px2) / 2

            # Person center is above motorcycle center (sitting on seat)
            vertical_ok = p_cy < mc_cy
            # Person is horizontally aligned with motorcycle
            horizontal_ok = abs(p_cx - mc_cx) < mc_w * 0.8
            # Person overlap with motorcycle bounding box
            overlap_ok = (px1 < mx2 and px2 > mx1 and py1 < my2 and py2 > my1)

            if vertical_ok and horizontal_ok and overlap_ok:
                return True

    return False


def _is_in_travel_lane(veh, image_shape):
    """Check if vehicle is positioned in an active traffic lane area.
    
    A vehicle in the central region of the image (not hugging edges)
    is likely in a travel lane.
    """
    h, w = image_shape[:2]
    x1, y1, x2, y2 = veh['bbox']
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    # Not hugging left/right edges (more than 12% from edges)
    edge_margin = w * 0.12
    not_at_edge = cx > edge_margin and cx < w - edge_margin

    # In middle 60% of image height (not at extreme top or bottom)
    vert_margin = h * 0.15
    in_mid_region = cy > vert_margin and cy < h - vert_margin

    return not_at_edge and in_mid_region


def check_illegal_parking(detections, image_shape, moving_vehicle_hint=False):
    """Detect possible illegal parking from single image.

    Only flags parking when:
    1. Vehicle appears stationary (not mounted rider in traffic lane)
    2. Parking context evidence exists (curb, footpath, no-parking zone)
    3. Vehicle occupies a blocking position

    Args:
        detections: list of detection dicts
        image_shape: (height, width, channels)
        moving_vehicle_hint: if True, skip parking analysis entirely

    Returns:
        list of violation dicts (empty unless strong parking evidence)
    """
    h, w = image_shape[:2]
    violations = []

    # FIX 3: Moving vehicle check — skip if rider mounted in travel lane
    if moving_vehicle_hint or _is_mounted_rider(detections):
        logger.debug("Skipping parking analysis: vehicle appears in active traffic flow")
        return violations

    vehicles = [d for d in detections if d['class_id'] in (2, 3, 5, 7)]
    persons = [d for d in detections if d['class_id'] == 0]
    if not vehicles:
        return violations

    # Check parking context
    has_context, context_clues = _has_parking_context(detections, image_shape)

    if not has_context:
        logger.debug("Skipping parking analysis: no parking context evidence")
        return violations

    for veh in vehicles:
        x1, y1, x2, y2 = veh['bbox']
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        box_w = x2 - x1
        box_h = y2 - y1

        # Skip if vehicle is in active travel lane (likely moving) UNLESS
        # there are pedestrians nearby suggesting roadside parking
        has_nearby_pedestrians = sum(
            1 for p in persons
            if abs((p['bbox'][1] + p['bbox'][3]) / 2 - cy) < h * 0.12
        ) >= 2
        if _is_in_travel_lane(veh, image_shape) and not has_nearby_pedestrians:
            continue

        reasons = []

        # Blocking footpath: vehicle occupies lower image region across pedestrian path
        footpath_zone_y = h * 0.80
        if y1 > footpath_zone_y and box_w > w * 0.35 and box_h > h * 0.15:
            reasons.append('vehicle positioned across pedestrian pathway')

        # Blocking lane: vehicle extends across lane markings
        if box_w > w * 0.5 and box_h > h * 0.2:
            reasons.append('vehicle extends across lane width')

        # Stationary on curb-side: vehicle hugging edge
        edge_margin = w * 0.05
        if (cx < edge_margin or cx > w - edge_margin) and box_h < h * 0.3:
            reasons.append('vehicle stationary at roadside edge')

        # Parked with nearby pedestrians in lower portion of image
        if has_nearby_pedestrians and cy > h * 0.5:
            nearby_count = sum(
                1 for p in persons
                if abs((p['bbox'][1] + p['bbox'][3]) / 2 - cy) < h * 0.12
            )
            if nearby_count >= 4:
                reasons.append('vehicle stationary with pedestrian activity at roadside')

        if reasons:
            vtype_label = config.VEHICLE_CLASSES.get(veh['class_id'], 'vehicle')
            violations.append({
                'violation_type': 'POSSIBLE_ILLEGAL_PARKING',
                'confidence': 0.45 + (len(reasons) * 0.1),
                'confidence_band': 'low',
                'severity_score': 25,
                'vehicle_bbox': veh['bbox'],
                'vehicle_type': vtype_label,
                'description': f'{veh.get("instance_id", vtype_label)} — Possible illegal parking: ' + '; '.join(reasons),
                'involved_objects': [veh.get('instance_id', 'vehicle')],
                'needs_review': True,
            })

    return violations
