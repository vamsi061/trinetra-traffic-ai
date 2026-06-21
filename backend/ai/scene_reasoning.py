"""Scene Reasoning Service for TRINETRA AI v2.

Understands traffic scenes using Florence-2 (when available) or template-based
reasoning derived from detected objects and spatial relationships.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def _describe_objects(detections, motorcycle_riders, crowded):
    """Generate human-readable scene description from detections."""
    labels = [d['label'] for d in detections]
    counts = {lbl: labels.count(lbl) for lbl in set(labels)}
    parts = []

    mc_count = counts.get('motorcycle', 0)
    person_count = counts.get('person', 0)
    car_count = counts.get('car', 0)
    truck_count = counts.get('truck', 0)
    bus_count = counts.get('bus', 0)

    if mc_count == 1:
        parts.append('One motorcycle')
    elif mc_count > 1:
        parts.append(f'{mc_count} motorcycles')

    if car_count == 1:
        parts.append('one car')
    elif car_count > 1:
        parts.append(f'{car_count} cars')
    if truck_count > 0:
        parts.append(f'{truck_count} truck{"s" if truck_count > 1 else ""}')
    if bus_count > 0:
        parts.append(f'{bus_count} bus{"es" if bus_count > 1 else ""}')

    if person_count == 1:
        parts.append('one person')
    elif person_count > 1:
        parts.append(f'{person_count} persons')

    if not parts:
        return 'No significant objects detected in the scene.'

    description = ', with '.join(parts)
    description = description[0].upper() + description[1:] + '.'

    if motorcycle_riders:
        rider_info = []
        for mc in motorcycle_riders:
            count = mc.get('rider_count', 1)
            est = mc.get('occupancy_estimate', f'{count} occupants')
            rider_info.append(est)
        description += f' Occupancy: {", ".join(rider_info)}.'
    if crowded:
        description += ' Scene is crowded.'

    return description


def _assess_road_conditions(detections, violations):
    """Assess road and traffic conditions."""
    conditions = []
    labels = [d['label'] for d in detections]

    if any(v.get('violation_type') == 'WRONG_SIDE_DRIVING' for v in violations):
        conditions.append('Wrong-side driving detected')
    if any(v.get('violation_type') == 'STOP_LINE_VIOLATION' for v in violations):
        conditions.append('Stop line violation observed')
    if any(v.get('violation_type') in ('RED_LIGHT_VIOLATION',) for v in violations):
        conditions.append('Red light running detected')

    if 'traffic light' in labels:
        conditions.append('Traffic signal present')
    if 'stop sign' in labels:
        conditions.append('Stop sign present')

    return conditions if conditions else ['Normal traffic conditions']


def _generate_narrative(detections, violations, motorcycle_riders, crowded,
                        license_plate, quality_score, enhancement_info):
    """Generate full narrative scene interpretation."""
    obj_desc = _describe_objects(detections, motorcycle_riders, crowded)
    road_conds = _assess_road_conditions(detections, violations)

    lines = [obj_desc]
    if road_conds:
        lines.append(' '.join(road_conds) + '.')

    if violations:
        vtypes = list(set(v.get('violation_type', v.get('type', ''))
                          for v in violations))
        if vtypes:
            vdesc = ', '.join(vt.replace('_', ' ').title() for vt in vtypes)
            lines.append(f'Violation(s) detected: {vdesc}.')

    if license_plate and license_plate.get('number'):
        lines.append(
            f'License plate {license_plate["number"]} '
            f'(confidence: {license_plate.get("confidence", 0)*100:.0f}%).'
        )

    if quality_score:
        lines.append(f'Image quality: {quality_score}.')

    if enhancement_info:
        steps = enhancement_info.get('steps_applied', [])
        if steps:
            lines.append(f'Enhancement applied: {", ".join(steps)}.')
        elif enhancement_info.get('failover_used'):
            lines.append('Enhancement skipped — quality already sufficient.')

    return ' '.join(lines)


class SceneReasoningService:
    """Vision-language scene reasoning for traffic images.

    Uses Florence-2 via transformers when available; falls back to
    template-based reasoning derived from object detections and violations.
    """

    def __init__(self):
        self._model = None
        self._processor = None
        self._loaded = False

    def _try_load_florence2(self):
        """Attempt to load Florence-2 model."""
        if self._loaded:
            return
        try:
            from transformers import AutoModelForCausalLM, AutoProcessor
            logger.info('Loading Florence-2...')
            model_id = 'microsoft/Florence-2-base'
            self._model = AutoModelForCausalLM.from_pretrained(
                model_id, trust_remote_code=True, local_files_only=False
            )
            self._processor = AutoProcessor.from_pretrained(
                model_id, trust_remote_code=True
            )
            self._loaded = True
            logger.info('Florence-2 loaded successfully')
        except Exception as e:
            logger.warning(f'Florence-2 unavailable: {e}. Using template fallback.')

    def reason(self, image, detections, violations, motorcycle_riders=None,
               crowded=False, license_plate=None, quality_score=None,
               enhancement_report=None):
        """Generate scene interpretation.

        Args:
            image: BGR image (numpy array)
            detections: list of detection dicts with label, confidence, bbox
            violations: list of violation dicts
            motorcycle_riders: list of rider association dicts
            crowded: bool
            license_plate: dict with number, confidence, visibility
            quality_score: str quality label
            enhancement_report: dict with enhancement info

        Returns:
            dict with narrative, analysis_type, confidence
        """
        self._try_load_florence2()

        if self._loaded and image is not None:
            try:
                return self._reason_with_florence(
                    image, detections, violations, motorcycle_riders,
                    crowded, license_plate
                )
            except Exception as e:
                logger.warning(f'Florence-2 inference failed: {e}. Using fallback.')

        return self._reason_template(
            detections, violations, motorcycle_riders, crowded,
            license_plate, quality_score, enhancement_report
        )

    def _reason_with_florence(self, image, detections, violations,
                               motorcycle_riders, crowded, license_plate):
        """Use Florence-2 for visual reasoning."""
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image is not None else None
        if rgb is None:
            raise ValueError('No image for Florence-2')

        task_prompt = '<CAPTION>'
        inputs = self._processor(text=task_prompt, images=rgb, return_tensors='pt')
        generated_ids = self._model.generate(
            input_ids=inputs['input_ids'],
            pixel_values=inputs['pixel_values'],
            max_new_tokens=200,
            num_beams=3,
        )
        caption = self._processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]

        return {
            'narrative': caption.strip(),
            'analysis_type': 'florence-2',
            'confidence': 0.75,
        }

    def _reason_template(self, detections, violations, motorcycle_riders,
                          crowded, license_plate, quality_score,
                          enhancement_report):
        """Generate scene description from detection data alone."""
        narrative = _generate_narrative(
            detections, violations, motorcycle_riders, crowded,
            license_plate, quality_score, enhancement_report
        )
        return {
            'narrative': narrative,
            'analysis_type': 'template',
            'confidence': 0.65,
        }

    def get_model_info(self):
        return {
            'type': 'SceneReasoningService',
            'model': 'Florence-2-base' if self._loaded else 'template-fallback',
            'loaded': self._loaded,
        }


import cv2
