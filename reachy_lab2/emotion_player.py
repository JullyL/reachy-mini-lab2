"""Emotions trajectoryPlayer.ts transition policy, ported for Python SDK playback.

MIT, Pollen Robotics Emotions cde39d23da61ada61d9ae4635bee051334434b44.
Ports computeInitialGotoDuration and headMagicMm; transport remains Python SDK.
"""
import numpy as np


def transition_duration(head, antennas, target_head=None, target_antennas=None):
    target_head = np.eye(4) if target_head is None else np.asarray(target_head)
    target_antennas = np.zeros(2) if target_antennas is None else np.asarray(target_antennas)
    head = np.asarray(head)
    translation_mm = np.linalg.norm(head[:3,3]-target_head[:3,3])*1000
    trace = np.sum(head[:3,:3]*target_head[:3,:3])
    angle_deg = np.rad2deg(np.arccos(np.clip((trace-1)/2,-1,1)))
    largest = max((translation_mm+angle_deg)*.02,
                  np.max(np.abs(np.rad2deg(np.asarray(antennas)-target_antennas)))*.005)
    return 0.0 if largest < .15 else float(np.clip(largest,.2,1.5))
