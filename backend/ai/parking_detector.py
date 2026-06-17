def check_illegal_parking(detections, image_shape):
    """Detect possible illegal parking from single image using heuristics.

    Indicators:
      - Vehicle near image edge (curb/lane boundary heuristic)
      - Vehicle blocking lower image region (pedestrian path heuristic)
      - Stationary vehicle in non-parking zone (center of road)

    Returns:
        list of violation dicts
    """
    h, w = image_shape[:2]
    violations = []

    vehicles = [d for d in detections if d['class_id'] in (2, 3, 5, 7)]

    for veh in vehicles:
        x1, y1, x2, y2 = veh['bbox']
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        box_w = x2 - x1
        box_h = y2 - y1

        reasons = []

        # Near left/right edge (curb parking)
        edge_margin = w * 0.08
        if cx < edge_margin or cx > w - edge_margin:
            reasons.append('vehicle near roadside edge')

        # Blocking lower region (pedestrian path / crossing area)
        lower_third = h * 0.66
        if y1 > lower_third and box_w > w * 0.4:
            reasons.append('vehicle blocking pedestrian pathway area')

        # Center of road blocking
        center_zone_x = w * 0.3
        center_zone_y = h * 0.2
        if (cx > center_zone_x and cx < w - center_zone_x and
                cy > center_zone_y and cy < h - center_zone_y and
                box_h > h * 0.15):
            reasons.append('vehicle detected in travel lane')

        if reasons:
            violations.append({
                'violation_type': 'POSSIBLE_ILLEGAL_PARKING',
                'confidence': 0.5 + (len(reasons) * 0.15),
                'confidence_band': 'medium' if len(reasons) <= 1 else 'low',
                'severity_score': 35,
                'description': 'Possible illegal parking detected: ' + '; '.join(reasons),
                'involved_objects': [veh.get('instance_id', 'vehicle')],
                'needs_review': True,
            })

    return violations
