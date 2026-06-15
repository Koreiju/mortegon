import time
from typing import List, Dict
import threading
from collections import deque

class WsReplayBuffer:
    """
    Per-ws-id circular buffer of emitted frames for resilient reconnection (§14.7).
    Provides a lossy replay buffer to catch up temporarily disconnected clients.
    """
    
    def __init__(self, max_age_seconds: int = 300, max_frames: int = 2048):
        self.max_age = max_age_seconds
        self.max_frames = max_frames
        self._buffers: Dict[str, deque] = {}
        self._seqs: Dict[str, int] = {}
        self._lock = threading.RLock()

    def record(self, ws_id: str, frame: dict) -> int:
        """Assign sequence id, append to buffer, return seq."""
        with self._lock:
            if ws_id not in self._buffers:
                self._buffers[ws_id] = deque(maxlen=self.max_frames)
                self._seqs[ws_id] = 0
            
            self._seqs[ws_id] += 1
            seq = self._seqs[ws_id]
            
            stored_frame = dict(frame)
            stored_frame['seq'] = seq
            stored_frame['_ts'] = time.time()
            
            self._buffers[ws_id].append(stored_frame)
            return seq

    def frames_since(self, ws_id: str, last_seq: int) -> List[dict]:
        """Return frames with seq > last_seq, or raise ValueError if the buffer rolled past last_seq."""
        with self._lock:
            if ws_id not in self._buffers:
                return []
            
            now = time.time()
            buf = self._buffers[ws_id]
            
            # Evict expired frames lazily
            while buf and now - buf[0]['_ts'] > self.max_age:
                buf.popleft()
            
            if not buf:
                return []
                
            first_seq = buf[0]['seq']
            if last_seq > 0 and last_seq < first_seq - 1:
                raise ValueError("ws_resume_expired")
                
            result = []
            for f in buf:
                if f['seq'] > last_seq:
                    ret_frame = dict(f)
                    ret_frame.pop('_ts', None)
                    result.append(ret_frame)
                    
            return result