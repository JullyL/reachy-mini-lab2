"""Summarize real trial logs and encode timestamped LIVE MuJoCo capture frames."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def encode(frames, root, output):
    import gstreamer_libs
    gstreamer_libs.setup_python_environment()
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    pipeline = Gst.parse_launch('appsrc name=source format=time caps="image/jpeg,framerate=15/1" ! jpegdec ! videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency bitrate=2000 ! h264parse ! mp4mux ! filesink name=dest')
    pipeline.get_by_name('dest').set_property('location', str(output))
    source = pipeline.get_by_name('source')
    pipeline.set_state(Gst.State.PLAYING)
    try:
        for i, row in enumerate(frames):
            data = (root/row['file']).read_bytes()
            if Path(row['file']).suffix.lower() == '.png':
                from io import BytesIO
                from PIL import Image
                converted = BytesIO()
                Image.open(BytesIO(data)).convert('RGB').save(converted, format='JPEG', quality=92)
                data = converted.getvalue()
            buf = Gst.Buffer.new_allocate(None, len(data), None)
            buf.fill(0, data)
            buf.pts = buf.dts = int((row['monotonic_s']-frames[0]['monotonic_s'])*Gst.SECOND)
            dt = frames[i+1]['monotonic_s']-row['monotonic_s'] if i+1 < len(frames) else 1/15
            buf.duration = int(dt*Gst.SECOND)
            if source.emit('push-buffer', buf) != Gst.FlowReturn.OK:
                raise RuntimeError('Video encoder rejected a real capture frame')
        source.emit('end-of-stream')
        msg = pipeline.get_bus().timed_pop_filtered(30*Gst.SECOND, Gst.MessageType.ERROR|Gst.MessageType.EOS)
        if msg is None or msg.type == Gst.MessageType.ERROR:
            raise RuntimeError(str(msg.parse_error()) if msg else 'Encoder timeout')
    finally:
        pipeline.set_state(Gst.State.NULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path)
    parser.add_argument('--frames', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--capture-only', action='store_true', help='Encode a complete live capture (e.g. Telepresence), without greeting-trial analysis')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    frames = [json.loads(x) for x in (args.frames/'frames.jsonl').read_text().splitlines()] if args.frames else []
    if args.capture_only:
        if len(frames) < 2:
            parser.error('--capture-only requires --frames with at least two captured frames')
        encode(frames, args.frames, args.out/'SIMULATION-live-capture.mp4')
        shutil.copyfile(args.frames/'frames.jsonl', args.out/'live-capture-frames.jsonl')
        return
    if args.runs is None:
        parser.error('--runs is required unless using --capture-only')
    summaries = []
    marker_lines = ['# Simulation stage markers', '', 'Each excerpt identifies its unmodified source JSONL and line number. Physical runs use the same logger.', '']
    for p in sorted(args.runs.glob('*.jsonl')):
        rows = [json.loads(x) for x in p.read_text().splitlines()]
        end = rows[-1]
        if end['marker'] != 'TRIAL_END':
            raise ValueError(f'Incomplete log: {p}')
        label = f"{end['condition']}-{end['antenna_amplitude_deg']:g}deg-{end['completion_status']}-{end['trial_id'][:8]}"
        feedback = [x for x in rows if x['marker']=='FEEDBACK']
        commands = [x for x in rows if x['marker']=='COMMAND']
        marker_lines += [f'## {label}', f'Source: `{p.as_posix()}`', '', '```text']
        marker_lines += [f"L{i}: {r['wall_time_utc']} {r['marker']} elapsed={r.get('elapsed_s')}" for i,r in enumerate(rows,1) if r['marker'] not in {'COMMAND','FEEDBACK'}]
        marker_lines += ['```', '']
        if feedback:
            fig, axes = plt.subplots(2,1,figsize=(8,5),sharex=True,layout='constrained')
            for side, ax in enumerate(axes):
                ax.plot([r['elapsed_s'] for r in commands],np.rad2deg([r['antennas_rad_right_left'][side] for r in commands]),label='Dispatched target',lw=1.3)
                ax.plot([r['elapsed_s'] for r in feedback],[r['angles_deg_right_left'][side] for r in feedback],label='Simulated SDK feedback',lw=1.3)
                for t in [1,5,6]:ax.axvline(t,color='.6',ls=':',lw=.8)
                ax.set_ylabel(('Right' if side==0 else 'Left')+' angle (deg)')
                ax.grid(alpha=.15)
            axes[0].legend(fontsize=8)
            axes[0].set_title('SIMULATION: '+label,fontsize=10)
            axes[1].set_xlabel('Seconds from PRE_HOLD_START; boundaries at 1, 5 and 6 s')
            fig.savefig(args.out/(label+'.png'),dpi=150)
            plt.close(fig)
        info = {'source':str(p),'trial_id':end['trial_id'],'condition':end['condition'],
            'amplitude_deg':end['antenna_amplitude_deg'],'commissioning':end['commissioning'],
            'status':end['completion_status'],'error':end['error'],
            'initial_neutral':next(r for r in rows if r['marker']=='INITIAL_NEUTRAL')['succeeded'],
            'baseline':next(r for r in rows if r['marker']=='BASELINE')['measured_neutral_deg_right_left'],
            'final_feedback':feedback[-1] if feedback else None,
            'recovery':next(r for r in rows if r['marker']=='NEUTRAL_RESULT'),
            'movement':end['measured_movement'],'skipped_frames':end['skipped_frames'],
            'speech_start_s':end['speech_start_s'],'movement_start_s':end['movement_start_s'],
            'movement_end_s':end['movement_end_s'],'sync_diagnostic_s':end['synchronization_error_s'],
            'max_dispatch_deviation_s':end['max_dispatch_deviation_s'],'software_checks_passed':end['software_checks_passed'],
            'study_eligible':end['study_eligible']}
        if frames:
            start = datetime.fromisoformat(rows[0]['wall_time_utc']).timestamp()-1
            stop = datetime.fromisoformat(end['wall_time_utc']).timestamp()+1
            selected = [r for r in frames if start <= r['utc_s'] <= stop]
            if len(selected)<2 or selected[0]['utc_s']>start+.2 or selected[-1]['utc_s']<stop-.2:
                raise ValueError(f'Capture does not cover entire trial and recovery: {label}')
            encode(selected,args.frames,args.out/('SIMULATION-'+label+'.mp4'))
            (args.out/(label+'-capture.json')).write_text(json.dumps({'basis':'Live running MuJoCo renderer; no replay or interpolation; no recorded audio',
                'source_frames':str(args.frames),'frames':selected,'trial_log':str(p)},indent=2)+'\n')
            info['video']='SIMULATION-'+label+'.mp4'
            info['capture_fps']=(len(selected)-1)/(selected[-1]['utc_s']-selected[0]['utc_s'])
            for name,target in [('start',start+1),('movement',start+3),('recovered',stop-.5)]:
                frame=min(selected,key=lambda r:abs(r['utc_s']-target))
                shutil.copyfile(args.frames/frame['file'],args.out/(f'SIMULATION-{label}-{name}.jpg'))
        summaries.append(info)
    (args.out/'results.json').write_text(json.dumps(summaries,indent=2)+'\n')
    (args.out/'stage-markers.md').write_text('\n'.join(marker_lines))
    table=['# New simulation results', '', 'SDK feedback is simulated. Audio timestamps predict DAC dispatch, not acoustic onset. No participant or physical data.', '',
        '| Condition | Amplitude | Outcome | Right / left max displacement | Neutral recovery | Poll Hz |', '|---|---:|---|---|---|---:|']
    for r in summaries:
        m=r['movement']
        excursion = f"{m['right']['maximum_abs_displacement_deg']:.3f}° / {m['left']['maximum_abs_displacement_deg']:.3f}°" if 'right' in m else 'Insufficient movement samples (early stop)'
        hz = f"{m['achieved_poll_hz']:.2f}" if 'achieved_poll_hz' in m else 'n/a'
        table.append(f"| {r['condition']} | {r['amplitude_deg']:g}° | {r['status']} | {excursion} | {r['recovery']['succeeded']} | {hz} |")
    (args.out/'RESULTS.md').write_text('\n'.join(table)+'\n')

if __name__=='__main__':main()
