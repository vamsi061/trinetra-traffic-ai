"""Scene Reasoning Service for TRINETRA AI v2.

Understands traffic scenes using Florence-2 (when available) or template-based
reasoning derived from detected objects and spatial relationships.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def _scene_composition(detections, motorcycle_riders):
    """Build structured scene breakdown.

    Returns dict with motorcycle_count, car_count, bus_count, truck_count,
    visible_persons, associated_riders, pedestrians.
    """
    labels = [d['label'] for d in detections]
    total_persons = labels.count('person')
    total_riders = sum(mc.get('rider_count', 0) for mc in (motorcycle_riders or []))
    pedestrians = max(0, total_persons - total_riders)

    return {
        'motorcycles': labels.count('motorcycle'),
        'cars': labels.count('car'),
        'buses': labels.count('bus'),
        'trucks': labels.count('truck'),
        'visible_persons': total_persons,
        'associated_riders': total_riders,
        'pedestrians': pedestrians,
        'bicycles': labels.count('bicycle'),
    }


def _officer_narrative(detections, violations, motorcycle_riders, crowded,
                       license_plate, quality_score, enhancement_info):
    """Generate officer-readable intelligence narrative."""
    comp = _scene_composition(detections, motorcycle_riders)
    lines = []

    mc_count = comp['motorcycles']
    car_count = comp['cars']
    bus_count = comp['buses']
    truck_count = comp['trucks']
    total_persons = comp['visible_persons']
    total_riders = comp['associated_riders']
    pedestrians = comp['pedestrians']

    if mc_count == 1:
        lines.append('One motorcycle detected.')
    elif mc_count > 1:
        lines.append(f'{mc_count} motorcycles detected.')
    if car_count == 1:
        lines.append('One car present.')
    elif car_count > 1:
        lines.append(f'{car_count} cars present.')
    if bus_count > 0:
        lines.append(f'{bus_count} bus{"es" if bus_count > 1 else ""} present.')
    if truck_count > 0:
        lines.append(f'{truck_count} truck{"s" if truck_count > 1 else ""} present.')

    if total_persons == 0:
        lines.append('No persons detected in the scene.')
    elif total_persons == 1:
        if total_riders == 1:
            lines.append('One individual is associated with a motorcycle as a rider.')
        else:
            lines.append('One person is visible in the scene and classified as a pedestrian.')
    else:
        lines.append(f'{total_persons} people visible in the scene.')
        if total_riders > 0:
            rider_label = 'individuals are' if total_riders > 1 else 'individual is'
            lines.append(
                f'{total_riders} {rider_label} associated with '
                f'{"a motorcycle" if mc_count == 1 else "motorcycles"} as riders.'
            )
        if pedestrians > 0:
            ped_label = 'additional individuals are' if pedestrians > 1 else 'additional individual is'
            lines.append(f'{pedestrians} {ped_label} classified as pedestrians.')

    if crowded:
        lines.append('Scene density is elevated — multiple subjects in frame.')

    return ' '.join(lines)


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
    obj_desc = _officer_narrative(detections, violations, motorcycle_riders,
                                   crowded, license_plate, quality_score,
                                   enhancement_info)
    road_conds = _assess_road_conditions(detections, violations)

    lines = [obj_desc]

    if road_conds:
        lines.append(' '.join(road_conds) + '.')

    if violations:
        vtypes = list(set(v.get('violation_type', v.get('type', ''))
                          for v in violations))
        if vtypes:
            vdesc = ', '.join(vt.replace('_', ' ').title() for vt in vtypes)
            lines.append(f'Observed Findings: {vdesc}.')

    if license_plate and license_plate.get('number'):
        lines.append(
            f'License plate {license_plate["number"]} '
            f'(OCR confidence: {license_plate.get("confidence", 0)*100:.0f}%).'
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
            import os
            os.environ['TORCHDYNAMO_DISABLE'] = '1'
            from transformers import AutoModelForCausalLM, AutoProcessor, PretrainedConfig
            logger.info('Loading Florence-2...')
            model_id = 'microsoft/Florence-2-base'
            self._processor = AutoProcessor.from_pretrained(
                model_id, trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                model_id, trust_remote_code=True, local_files_only=False,
                attn_implementation='eager'
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
            dict with narrative, analysis_type, confidence, scene_breakdown
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
            use_cache=False,
        )
        caption = self._processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]

        breakdown = _scene_composition(detections, motorcycle_riders)

        return {
            'narrative': caption.strip(),
            'analysis_type': 'florence-2',
            'confidence': 0.75,
            'scene_breakdown': breakdown,
        }

    def _reason_template(self, detections, violations, motorcycle_riders,
                          crowded, license_plate, quality_score,
                          enhancement_report):
        """Generate scene description from detection data alone."""
        breakdown = _scene_composition(detections, motorcycle_riders)
        narrative = _generate_narrative(
            detections, violations, motorcycle_riders, crowded,
            license_plate, quality_score, enhancement_report
        )
        return {
            'narrative': narrative,
            'analysis_type': 'template',
            'confidence': 0.65,
            'scene_breakdown': breakdown,
        }

    def get_model_info(self):
        return {
            'type': 'SceneReasoningService',
            'model': 'Florence-2-base' if self._loaded else 'template-fallback',
            'loaded': self._loaded,
        }


import cv2
