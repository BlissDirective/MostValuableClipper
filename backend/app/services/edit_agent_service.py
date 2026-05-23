"""Edit Swarm Agent System for autonomous clip enhancement.

Each agent specializes in one editing dimension and outputs a recipe
that FFmpegEditService can execute. Agents can run individually or
be orchestrated together for full auto-editing.
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import random

class AgentCapability(Enum):
    STICKER = "sticker"
    TRANSITION = "transition"
    MUSIC = "music"
    COLOR = "color"
    CAPTION = "caption"
    PACING = "pacing"
    THUMBNAIL = "thumbnail"

class EditAgent:
    """Base class for all edit agents."""
    
    def __init__(self, capability: AgentCapability):
        self.capability = capability
        self.cost_estimate = 0.0  # USD per clip
        self.quality_score = 0.5  # 0-1
    
    async def analyze(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze clip and return enhancement suggestions."""
        raise NotImplementedError
    
    async def generate_recipe(self, clip_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an edit recipe for FFmpegEditService."""
        raise NotImplementedError


class StickerAgent(EditAgent):
    """Agent that adds stickers, emoji, and brand overlays to clips."""
    
    def __init__(self):
        super().__init__(AgentCapability.STICKER)
        self.cost_estimate = 0.01
        self.quality_score = 0.7
    
    STICKER_LIBRARY = {
        "reactions": {
            "fire": "https://cdn.blissclip.io/stickers/fire.png",
            "heart": "https://cdn.blissclip.io/stickers/heart.png",
            "star": "https://cdn.blissclip.io/stickers/star.png",
            "laugh": "https://cdn.blissclip.io/stickers/laugh.png",
            "shock": "https://cdn.blissclip.io/stickers/shock.png",
        },
        "badges": {
            "new": "https://cdn.blissclip.io/stickers/badge-new.png",
            "trending": "https://cdn.blissclip.io/stickers/badge-trending.png",
            "viral": "https://cdn.blissclip.io/stickers/badge-viral.png",
        },
        "cta": {
            "subscribe": "https://cdn.blissclip.io/stickers/cta-subscribe.png",
            "follow": "https://cdn.blissclip.io/stickers/cta-follow.png",
            "link_in_bio": "https://cdn.blissclip.io/stickers/cta-link.png",
        }
    }
    
    POSITION_PRESETS = {
        "top_left": {"x": 20, "y": 20},
        "top_right": {"x": -20, "y": 20},
        "bottom_left": {"x": 20, "y": -20},
        "bottom_right": {"x": -20, "y": -20},
        "center": {"x": "(W-w)/2", "y": "(H-h)/2"},
    }
    
    async def analyze(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        caption = clip_data.get("caption", "")
        platform = clip_data.get("platform", "tiktok")
        
        suggestions = []
        
        if any(word in caption.lower() for word in ["new", "launch", "announce"]):
            suggestions.append({"sticker": "new", "position": "top_right", "scale": 0.8})
        
        if any(word in caption.lower() for word in ["funny", "laugh", "haha", "lol"]):
            suggestions.append({"sticker": "laugh", "position": "bottom_left", "scale": 0.6})
        
        if any(word in caption.lower() for word in ["love", "heart", "amazing", "best"]):
            suggestions.append({"sticker": "heart", "position": "top_left", "scale": 0.5})
        
        if platform == "tiktok":
            suggestions.append({"sticker": "follow", "position": "bottom_right", "scale": 0.7})
        elif platform == "youtube":
            suggestions.append({"sticker": "subscribe", "position": "bottom_right", "scale": 0.7})
        
        if not suggestions:
            suggestions.append({"sticker": "star", "position": "top_right", "scale": 0.4})
        
        return {
            "suggested_stickers": suggestions,
            "library": self.STICKER_LIBRARY
        }
    
    async def generate_recipe(self, clip_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        analysis = await self.analyze(clip_data)
        stickers = settings.get("stickers", analysis["suggested_stickers"])
        
        overlays = []
        for s in stickers:
            sticker_id = s.get("sticker", "star")
            position_key = s.get("position", "top_right")
            scale = s.get("scale", 0.5)
            start = s.get("start", 0)
            end = s.get("end", clip_data.get("duration", 30))
            
            pos = self.POSITION_PRESETS.get(position_key, self.POSITION_PRESETS["top_right"])
            
            overlays.append({
                "url": self._resolve_sticker_url(sticker_id),
                "x": pos["x"],
                "y": pos["y"],
                "scale": scale,
                "start": start,
                "end": end
            })
        
        return {"stickers": overlays}
    
    def _resolve_sticker_url(self, sticker_id: str) -> str:
        for category in self.STICKER_LIBRARY.values():
            if sticker_id in category:
                return category[sticker_id]
        return self.STICKER_LIBRARY["reactions"]["star"]


class TransitionAgent(EditAgent):
    """Agent that applies transitions between segments or clips."""
    
    def __init__(self):
        super().__init__(AgentCapability.TRANSITION)
        self.cost_estimate = 0.02
        self.quality_score = 0.8
    
    TRANSITION_LIBRARY = {
        "fade": {"duration": 0.5, "complexity": "low"},
        "dissolve": {"duration": 0.6, "complexity": "low"},
        "wipe_left": {"duration": 0.4, "complexity": "medium"},
        "wipe_right": {"duration": 0.4, "complexity": "medium"},
        "slide_up": {"duration": 0.5, "complexity": "medium"},
        "slide_down": {"duration": 0.5, "complexity": "medium"},
        "zoom_in": {"duration": 0.6, "complexity": "medium"},
        "zoom_out": {"duration": 0.6, "complexity": "medium"},
        "spin": {"duration": 0.7, "complexity": "high"},
        "pixelate": {"duration": 0.5, "complexity": "high"},
    }
    
    async def analyze(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        duration = clip_data.get("duration", 30)
        segments = clip_data.get("segments", [])
        platform = clip_data.get("platform", "tiktok")
        
        if not segments or len(segments) < 2:
            segments = [{"start": 0, "end": duration / 2}, {"start": duration / 2, "end": duration}]
        
        suggestions = []
        
        if platform in ("tiktok", "instagram"):
            for i in range(len(segments) - 1):
                trans = random.choice(["zoom_in", "slide_up", "spin"])
                suggestions.append({
                    "between_segments": [i, i + 1],
                    "type": trans,
                    "duration": 0.3
                })
        elif platform == "youtube":
            for i in range(len(segments) - 1):
                suggestions.append({
                    "between_segments": [i, i + 1],
                    "type": "fade",
                    "duration": 0.5
                })
        else:
            for i in range(len(segments) - 1):
                suggestions.append({
                    "between_segments": [i, i + 1],
                    "type": "dissolve",
                    "duration": 0.4
                })
        
        return {
            "suggested_transitions": suggestions,
            "library": self.TRANSITION_LIBRARY
        }
    
    async def generate_recipe(self, clip_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        analysis = await self.analyze(clip_data)
        transitions = settings.get("transitions", analysis["suggested_transitions"])
        
        segments = clip_data.get("segments")
        if not segments:
            duration = clip_data.get("duration", 30)
            mid = duration / 2
            segments = [{"start": 0, "end": mid}, {"start": mid, "end": duration}]
        
        return {
            "segments": segments,
            "transitions": transitions
        }


class MusicAgent(EditAgent):
    """Agent that handles background music, beat sync, and audio ducking."""
    
    def __init__(self):
        super().__init__(AgentCapability.MUSIC)
        self.cost_estimate = 0.03
        self.quality_score = 0.85
    
    MUSIC_LIBRARY = {
        "upbeat": {
            "energy_high": "https://cdn.blissclip.io/music/upbeat-energy.mp3",
            "pop_1": "https://cdn.blissclip.io/music/upbeat-pop-1.mp3",
            "pop_2": "https://cdn.blissclip.io/music/upbeat-pop-2.mp3",
        },
        "chill": {
            "lofi_1": "https://cdn.blissclip.io/music/chill-lofi-1.mp3",
            "ambient": "https://cdn.blissclip.io/music/chill-ambient.mp3",
        },
        "dramatic": {
            "cinematic": "https://cdn.blissclip.io/music/dramatic-cinematic.mp3",
            "epic": "https://cdn.blissclip.io/music/dramatic-epic.mp3",
        },
        "trending": {
            "viral_1": "https://cdn.blissclip.io/music/trending-viral-1.mp3",
            "viral_2": "https://cdn.blissclip.io/music/trending-viral-2.mp3",
        }
    }
    
    async def analyze(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        caption = clip_data.get("caption", "")
        duration = clip_data.get("duration", 30)
        platform = clip_data.get("platform", "tiktok")
        
        mood = "upbeat"
        if any(w in caption.lower() for w in ["sad", "emotional", "deep", "thought"]):
            mood = "chill"
        elif any(w in caption.lower() for w in ["epic", "amazing", "wow", "unbelievable"]):
            mood = "dramatic"
        elif platform == "tiktok":
            mood = "trending"
        
        tracks = list(self.MUSIC_LIBRARY.get(mood, self.MUSIC_LIBRARY["upbeat"]).values())
        selected = random.choice(tracks) if tracks else None
        
        return {
            "suggested_mood": mood,
            "suggested_track": selected,
            "volume": 0.25,
            "fade_in": 1.0,
            "fade_out": 2.0,
            "loop": duration > 60,
            "library": self.MUSIC_LIBRARY
        }
    
    async def generate_recipe(self, clip_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        analysis = await self.analyze(clip_data)
        
        track_url = settings.get("track_url", analysis["suggested_track"])
        volume = settings.get("volume", analysis["volume"])
        fade_in = settings.get("fade_in", analysis["fade_in"])
        fade_out = settings.get("fade_out", analysis["fade_out"])
        loop = settings.get("loop", analysis["loop"])
        
        if not track_url:
            return {"audio": "keep"}
        
        return {
            "audio": f"replace:{track_url}",
            "music_volume": volume,
            "music_fade_in": fade_in,
            "music_fade_out": fade_out,
            "music_loop": loop,
            "ducking": settings.get("ducking", True)
        }


class ColorAgent(EditAgent):
    """Agent that applies color grading optimized per platform."""
    
    def __init__(self):
        super().__init__(AgentCapability.COLOR)
        self.cost_estimate = 0.015
        self.quality_score = 0.75
    
    LUT_PRESETS = {
        "tiktok": {"saturation": 1.2, "contrast": 1.1, "brightness": 0.05, "vibrance": 1.3},
        "instagram": {"saturation": 1.1, "contrast": 1.05, "brightness": 0.0, "vibrance": 1.15},
        "youtube": {"saturation": 1.0, "contrast": 1.05, "brightness": 0.0, "vibrance": 1.0},
    }
    
    async def analyze(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        platform = clip_data.get("platform", "tiktok")
        return {
            "suggested_preset": platform,
            "presets": self.LUT_PRESETS
        }
    
    async def generate_recipe(self, clip_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        analysis = await self.analyze(clip_data)
        preset = settings.get("preset", analysis["suggested_preset"])
        lut = self.LUT_PRESETS.get(preset, self.LUT_PRESETS["tiktok"])
        
        filters = []
        
        eq_params = []
        if lut["saturation"] != 1.0:
            eq_params.append(f"saturation={lut['saturation']}")
        if lut["contrast"] != 1.0:
            eq_params.append(f"contrast={lut['contrast']}")
        if lut["brightness"] != 0:
            eq_params.append(f"brightness={lut['brightness']}")
        
        if eq_params:
            filters.append(f"eq={':'.join(eq_params)}")
        
        if lut["vibrance"] != 1.0:
            v = lut["vibrance"]
            filters.append(f"colorchannelmixer={v}:0.2:0.2:0:0.2:{v}:0.2:0:0.2:0.2:{v}")
        
        return {"filters": filters}


class CaptionAgent(EditAgent):
    """Agent that generates and styles captions."""
    
    def __init__(self):
        super().__init__(AgentCapability.CAPTION)
        self.cost_estimate = 0.02
        self.quality_score = 0.9
    
    FONT_PRESETS = {
        "tiktok": {"font": "Arial-Bold", "size": 36, "color": "white", "border": "black"},
        "instagram": {"font": "Helvetica-Bold", "size": 32, "color": "white", "border": "black"},
        "youtube": {"font": "Roboto-Bold", "size": 28, "color": "white", "border": "black"},
    }
    
    async def analyze(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        platform = clip_data.get("platform", "tiktok")
        caption = clip_data.get("caption", "")
        transcript = clip_data.get("transcript", "")
        
        return {
            "has_transcript": bool(transcript),
            "suggested_style": self.FONT_PRESETS.get(platform, self.FONT_PRESETS["tiktok"]),
            "word_count": len(caption.split()) if caption else 0
        }
    
    async def generate_recipe(self, clip_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        analysis = await self.analyze(clip_data)
        style = settings.get("style", analysis["suggested_style"])
        caption_text = settings.get("caption", clip_data.get("caption", ""))
        
        if not caption_text:
            return {}
        
        return {
            "caption": caption_text,
            "caption_style": style
        }


class PacingAgent(EditAgent):
    """Agent that optimizes clip pacing with speed ramps and jump cuts."""
    
    def __init__(self):
        super().__init__(AgentCapability.PACING)
        self.cost_estimate = 0.025
        self.quality_score = 0.8
    
    async def analyze(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        duration = clip_data.get("duration", 30)
        platform = clip_data.get("platform", "tiktok")
        
        if platform == "tiktok" and duration > 30:
            return {
                "suggested_speed": 1.2,
                "reason": "TikTok performs better under 30s; slight speedup helps"
            }
        elif duration > 60:
            return {
                "suggested_speed": 1.1,
                "reason": "Long clip; mild speedup maintains engagement"
            }
        
        return {"suggested_speed": 1.0, "reason": "Duration optimal"}
    
    async def generate_recipe(self, clip_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        analysis = await self.analyze(clip_data)
        speed = settings.get("speed", analysis["suggested_speed"])
        
        if speed == 1.0:
            return {}
        
        return {"speed": speed}


class ThumbnailAgent(EditAgent):
    """Agent that generates platform-optimized thumbnails."""
    
    def __init__(self):
        super().__init__(AgentCapability.THUMBNAIL)
        self.cost_estimate = 0.01
        self.quality_score = 0.75
    
    ASPECT_RATIOS = {
        "tiktok": "9:16",
        "instagram": "4:5",
        "youtube": "16:9",
        "twitter": "16:9"
    }
    
    async def analyze(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        platform = clip_data.get("platform", "tiktok")
        duration = clip_data.get("duration", 30)
        best_time = duration * 0.25
        
        return {
            "suggested_timestamp": best_time,
            "aspect_ratio": self.ASPECT_RATIOS.get(platform, "16:9"),
            "overlay_text": clip_data.get("caption", "")[:30]
        }
    
    async def generate_recipe(self, clip_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        analysis = await self.analyze(clip_data)
        
        return {
            "thumbnail": {
                "timestamp": settings.get("timestamp", analysis["suggested_timestamp"]),
                "aspect_ratio": analysis["aspect_ratio"],
                "overlay": settings.get("overlay_text", analysis["overlay_text"])
            }
        }


class EditSwarm:
    """Orchestrates multiple EditAgents to produce a combined edit recipe."""
    
    AGENT_REGISTRY: Dict[AgentCapability, type] = {
        AgentCapability.STICKER: StickerAgent,
        AgentCapability.TRANSITION: TransitionAgent,
        AgentCapability.MUSIC: MusicAgent,
        AgentCapability.COLOR: ColorAgent,
        AgentCapability.CAPTION: CaptionAgent,
        AgentCapability.PACING: PacingAgent,
        AgentCapability.THUMBNAIL: ThumbnailAgent,
    }
    
    def __init__(self):
        self._agents: Dict[AgentCapability, EditAgent] = {}
    
    def get_agent(self, capability: AgentCapability) -> EditAgent:
        if capability not in self._agents:
            agent_class = self.AGENT_REGISTRY[capability]
            self._agents[capability] = agent_class()
        return self._agents[capability]
    
    async def run(
        self,
        clip_data: Dict[str, Any],
        agents: List[str],
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run selected agents and merge their recipes."""
        settings = settings or {}
        merged_recipe: Dict[str, Any] = {}
        total_cost = 0.0
        agent_results = []
        
        for agent_name in agents:
            try:
                capability = AgentCapability(agent_name)
                agent = self.get_agent(capability)
                
                agent_settings = settings.get(agent_name, {})
                recipe = await agent.generate_recipe(clip_data, agent_settings)
                
                for key, value in recipe.items():
                    if key in merged_recipe and isinstance(value, list):
                        if isinstance(merged_recipe[key], list):
                            merged_recipe[key].extend(value)
                        else:
                            merged_recipe[key] = value
                    else:
                        merged_recipe[key] = value
                
                total_cost += agent.cost_estimate
                agent_results.append({
                    "agent": agent_name,
                    "success": True,
                    "recipe_keys": list(recipe.keys())
                })
                
            except Exception as e:
                agent_results.append({
                    "agent": agent_name,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "recipe": merged_recipe,
            "agents_run": agent_results,
            "total_cost_estimate": round(total_cost, 3),
            "clip_id": clip_data.get("id")
        }
    
    async def analyze_clip(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run analysis on all agents and return suggestions."""
        suggestions = {}
        
        for capability, agent_class in self.AGENT_REGISTRY.items():
            try:
                agent = agent_class()
                analysis = await agent.analyze(clip_data)
                suggestions[capability.value] = {
                    "analysis": analysis,
                    "cost": agent.cost_estimate,
                    "quality": agent.quality_score
                }
            except Exception as e:
                suggestions[capability.value] = {"error": str(e)}
        
        return suggestions