import os
import uuid
import hashlib
import asyncio
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict
import aiohttp
from PIL import Image
from io import BytesIO

@dataclass
class MediaAsset:
    asset_id: str               # UUID
    source_url: str             # original URL on the page
    local_path: str             # media/<domain>/<hash>.<ext>
    content_hash: str           # SHA256 of file content
    mime_type: str
    file_size: int              # bytes
    width: Optional[int]        # pixels (images, video)
    height: Optional[int]
    duration: Optional[float]   # seconds (audio, video)
    phash: Optional[str]        # perceptual hash (images)
    thumbnail_path: Optional[str]
    source_xpath: str           # xpath of the DOM node
    snapshot_id: str            # FK to DomSnapshot
    created_at: str

class MediaPipeline:
    """Download, cache, and extract metadata for all media in a snapshot."""

    def __init__(self, cache_dir: str = 'media',
                 max_file_size: int = 2_000_000,
                 max_total_size: int = 50_000_000,
                 max_concurrent: int = 4):
        self.cache_dir = cache_dir
        self.max_file = max_file_size
        self.max_total = max_total_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            
    async def process_snapshot(self, snapshot_id: str,
                               media_xpaths: Dict[str, str]
                               ) -> List[MediaAsset]:
        assets = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for xpath, url in media_xpaths.items():
                if not url.startswith('http'):
                    continue
                tasks.append(self._process_single(session, snapshot_id, xpath, url))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, MediaAsset):
                    assets.append(res)
        return assets

    async def _process_single(self, session: aiohttp.ClientSession,
                              snapshot_id: str, xpath: str, url: str) -> Optional[MediaAsset]:
        async with self.semaphore:
            try:
                domain = url.split('/')[2] if '//' in url else 'unknown'
                data, mime = await self._download_one(session, url)
                if not data:
                    return None
                    
                content_hash = hashlib.sha256(data).hexdigest()
                ext = mime.split('/')[-1] if '/' in mime else 'bin'
                domain_dir = os.path.join(self.cache_dir, domain)
                os.makedirs(domain_dir, exist_ok=True)
                
                local_path = os.path.join(domain_dir, f"{content_hash}.{ext}")
                if not os.path.exists(local_path):
                    with open(local_path, 'wb') as f:
                        f.write(data)
                        
                meta = self._extract_metadata(data, mime)
                thumb_path = None
                if meta.get('width') and meta.get('height') and mime.startswith('image'):
                    thumb_path = self._generate_thumbnail(data, local_path)
                    
                return MediaAsset(
                    asset_id=str(uuid.uuid4()),
                    source_url=url,
                    local_path=local_path,
                    content_hash=content_hash,
                    mime_type=mime,
                    file_size=len(data),
                    width=meta.get('width'),
                    height=meta.get('height'),
                    duration=None,
                    phash=None,
                    thumbnail_path=thumb_path,
                    source_xpath=xpath,
                    snapshot_id=snapshot_id,
                    created_at=datetime.utcnow().isoformat()
                )
            except Exception as e:
                print(f"Failed to process media {url}: {e}")
                return None

    async def _download_one(self, session: aiohttp.ClientSession, url: str):
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    if len(data) > self.max_file:
                        return None, None
                    mime = resp.headers.get('Content-Type', 'application/octet-stream')
                    return data, mime
        except Exception:
            pass
        return None, None

    def _extract_metadata(self, data: bytes, mime: str) -> Dict:
        meta = {}
        if mime.startswith('image'):
            try:
                img = Image.open(BytesIO(data))
                meta['width'], meta['height'] = img.size
            except:
                pass
        return meta

    def _generate_thumbnail(self, data: bytes, original_path: str) -> Optional[str]:
        try:
            thumb_path = original_path.rsplit('.', 1)[0] + '_thumb.jpg'
            if os.path.exists(thumb_path):
                return thumb_path
            img = Image.open(BytesIO(data))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.thumbnail((128, 128))
            img.save(thumb_path, 'JPEG')
            return thumb_path
        except:
            return None
