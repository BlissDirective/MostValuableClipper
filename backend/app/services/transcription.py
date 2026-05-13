import os
import tempfile
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

class TranscriptionService:
    """Audio transcription using OpenAI Whisper API."""
    
    BASE_URL = "https://api.openai.com/v1"
    
    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper."""
        api_key = settings.OPENAI_API_KEY
        
        if not api_key:
            # Fallback: return empty transcription for development
            return {
                "text": "",
                "segments": [],
                "language": "en",
                "duration": 0
            }
        
        async with httpx.AsyncClient() as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    f"{self.BASE_URL}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": (os.path.basename(audio_path), f, "audio/wav")},
                    data={
                        "model": "whisper-1",
                        "response_format": "verbose_json",
                        "timestamp_granularities": ["segment"]
                    },
                    timeout=300
                )
            
            response.raise_for_status()
            return response.json()
    
    async def transcribe_with_diarization(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe with speaker identification (premium feature)."""
        # For now, return basic transcription
        # TODO: Implement speaker diarization using pyannote or similar
        return await self.transcribe(audio_path)
    
    def find_interesting_segments(
        self,
        transcription: Dict[str, Any],
        min_duration: float = 15,
        max_duration: float = 90,
        num_clips: int = 5
    ) -> List[Dict[str, Any]]:
        """Find the most interesting segments from transcription."""
        segments = transcription.get("segments", [])
        
        if not segments:
            return []
        
        # Score segments by various factors
        scored_segments = []
        
        for segment in segments:
            score = 0
            text = segment.get("text", "").strip()
            
            # Length score (prefer medium-length segments)
            duration = segment.get("end", 0) - segment.get("start", 0)
            if min_duration <= duration <= max_duration:
                score += 10
            elif duration < min_duration:
                score -= 5
            else:
                score -= 2
            
            # Content signals
            # Questions often indicate engagement
            if "?" in text:
                score += 3
            
            # Exclamations show excitement
            if "!" in text:
                score += 2
            
            # Numbers/stats are interesting
            if any(c.isdigit() for c in text):
                score += 2
            
            # Key phrases that indicate value
            value_phrases = [
                "secret", "tip", "trick", "hack", "revealed",
                "surprising", "shocking", "amazing", "insane",
                "discover", "learn", "understand", "how to",
                "why", "what if", "imagine", "remember"
            ]
            
            text_lower = text.lower()
            for phrase in value_phrases:
                if phrase in text_lower:
                    score += 2
                    break
            
            # Avoid boring segments
            boring_phrases = ["um", "uh", "like", "you know", "so yeah"]
            for phrase in boring_phrases:
                if text_lower.count(phrase) > 2:
                    score -= 3
                    break
            
            scored_segments.append({
                **segment,
                "score": score,
                "duration": duration
            })
        
        # Sort by score and pick top segments
        scored_segments.sort(key=lambda x: x["score"], reverse=True)
        
        # Ensure segments don't overlap too much
        selected = []
        for seg in scored_segments:
            if len(selected) >= num_clips:
                break
            
            # Check for overlap with already selected segments
            overlaps = False
            for sel in selected:
                if (seg["start"] < sel["end"] + 2 and seg["end"] > sel["start"] - 2):
                    overlaps = True
                    break
            
            if not overlaps:
                selected.append(seg)
        
        return selected
