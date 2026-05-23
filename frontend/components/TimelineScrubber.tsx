import React, { useCallback, useState, useRef, useEffect, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  Image,
  PanResponder,
  GestureResponderEvent,
  PanResponderGestureState,
  LayoutChangeEvent,
} from "react-native";
import { Scissors } from "lucide-react-native";
import { tokens } from "@/constants/tokens";

export interface Thumbnail {
  time: number;
  url: string;
}

interface TimelineScrubberProps {
  thumbnails: Thumbnail[];
  duration: number;
  startTime: number;
  endTime: number;
  onStartTimeChange: (time: number) => void;
  onEndTimeChange: (time: number) => void;
  currentTime?: number;
  onCurrentTimeChange?: (time: number) => void;
}

export default function TimelineScrubber({
  thumbnails,
  duration,
  startTime,
  endTime,
  onStartTimeChange,
  onEndTimeChange,
  currentTime = 0,
  onCurrentTimeChange,
}: TimelineScrubberProps) {
  const [containerWidth, setContainerWidth] = useState(0);
  const [isDragging, setIsDragging] = useState<"start" | "end" | "current" | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);

  const pixelsPerSecond = containerWidth > 0 ? containerWidth / duration : 1;

  const handleLayout = useCallback((event: LayoutChangeEvent) => {
    setContainerWidth(event.nativeEvent.layout.width);
  }, []);

  const timeToX = useCallback((time: number) => {
    return (time / duration) * containerWidth;
  }, [duration, containerWidth]);

  const xToTime = useCallback((x: number) => {
    const time = (x / containerWidth) * duration;
    return Math.max(0, Math.min(duration, time));
  }, [duration, containerWidth]);

  const createPanResponder = useCallback((handle: "start" | "end" | "current") => {
    return PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        setIsDragging(handle);
      },
      onPanResponderMove: (_, gestureState: PanResponderGestureState) => {
        const newX = Math.max(0, Math.min(containerWidth, gestureState.moveX));
        const newTime = xToTime(newX);
        
        if (handle === "start") {
          const clampedTime = Math.min(newTime, endTime - 0.5);
          onStartTimeChange(Math.round(clampedTime * 10) / 10);
        } else if (handle === "end") {
          const clampedTime = Math.max(newTime, startTime + 0.5);
          onEndTimeChange(Math.round(clampedTime * 10) / 10);
        } else if (handle === "current" && onCurrentTimeChange) {
          onCurrentTimeChange(Math.round(newTime * 10) / 10);
        }
      },
      onPanResponderRelease: () => {
        setIsDragging(null);
      },
    });
  }, [containerWidth, xToTime, startTime, endTime, onStartTimeChange, onEndTimeChange, onCurrentTimeChange]);

  const startPanResponder = useMemo(() => createPanResponder("start"), [createPanResponder]);
  const endPanResponder = useMemo(() => createPanResponder("end"), [createPanResponder]);
  const currentPanResponder = useMemo(() => createPanResponder("current"), [createPanResponder]);

  // Format time helper
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${mins}:${secs.toString().padStart(2, "0")}.${ms}`;
  };

  return (
    <View style={styles.container}>
      {/* Time labels */}
      <View style={styles.timeLabels}>
        <Text style={styles.timeText}>{formatTime(startTime)}</Text>
        <Text style={styles.durationText}>{formatTime(currentTime)}</Text>
        <Text style={styles.timeText}>{formatTime(endTime)}</Text>
      </View>

      {/* Timeline track */}
      <View style={styles.track} onLayout={handleLayout}>
        {/* Thumbnail strip */}
        <View style={styles.thumbnailContainer}>
          {thumbnails.map((thumb, index) => (
            <Image
              key={index}
              source={{ uri: thumb.url }}
              style={styles.thumbnail}
              resizeMode="cover"
            />
          ))}
        </View>

        {/* Unselected regions (dark overlay) */}
        <View
          style={[
            styles.unselectedLeft,
            { width: timeToX(startTime) },
          ]}
        />
        <View
          style={[
            styles.unselectedRight,
            { left: timeToX(endTime), width: containerWidth - timeToX(endTime) },
          ]}
        />

        {/* Current time indicator */}
        {onCurrentTimeChange && (
          <View
            {...currentPanResponder.panHandlers}
            style={[
              styles.currentIndicator,
              { left: timeToX(currentTime) - 1 },
            ]}
          >
            <View style={styles.currentLine} />
          </View>
        )}

        {/* Start handle */}
        <View
          {...startPanResponder.panHandlers}
          style={[
            styles.handle,
            styles.startHandle,
            { left: timeToX(startTime) - 12 },
            isDragging === "start" && styles.handleActive,
          ]}
        >
          <Scissors size={14} color={tokens.color.brand.indigo[300]} />
          <View style={styles.handleLine} />
        </View>

        {/* End handle */}
        <View
          {...endPanResponder.panHandlers}
          style={[
            styles.handle,
            styles.endHandle,
            { left: timeToX(endTime) - 12 },
            isDragging === "end" && styles.handleActive,
          ]}
        >
          <Scissors size={14} color={tokens.color.brand.indigo[300]} />
          <View style={styles.handleLine} />
        </View>

        {/* Selected range highlight */}
        <View
          style={[
            styles.selectedRange,
            {
              left: timeToX(startTime),
              width: timeToX(endTime) - timeToX(startTime),
            },
          ]}
        />
      </View>

      {/* Duration label */}
      <Text style={styles.totalDuration}>Total: {formatTime(duration)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 8,
  },
  timeLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 4,
  },
  timeText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.secondary,
  },
  durationText: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.brand.indigo[400],
    fontWeight: "600",
  },
  track: {
    height: 72,
    borderRadius: tokens.radius.md,
    overflow: "hidden",
    backgroundColor: tokens.color.bg.surface,
    position: "relative",
  },
  thumbnailContainer: {
    flexDirection: "row",
    height: 72,
    gap: 1,
  },
  thumbnail: {
    flex: 1,
    height: 72,
    backgroundColor: tokens.color.bg.elevated,
  },
  unselectedLeft: {
    position: "absolute",
    top: 0,
    left: 0,
    height: 72,
    backgroundColor: "rgba(0,0,0,0.6)",
  },
  unselectedRight: {
    position: "absolute",
    top: 0,
    height: 72,
    backgroundColor: "rgba(0,0,0,0.6)",
  },
  selectedRange: {
    position: "absolute",
    top: 68,
    height: 4,
    backgroundColor: tokens.color.brand.indigo[500],
  },
  handle: {
    position: "absolute",
    top: 0,
    width: 24,
    height: 72,
    alignItems: "center",
    justifyContent: "flex-start",
    paddingTop: 4,
    zIndex: 10,
  },
  startHandle: {
    backgroundColor: "rgba(99, 102, 241, 0.3)",
    borderTopLeftRadius: tokens.radius.md,
    borderBottomLeftRadius: tokens.radius.md,
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.brand.indigo[500],
  },
  endHandle: {
    backgroundColor: "rgba(99, 102, 241, 0.3)",
    borderTopRightRadius: tokens.radius.md,
    borderBottomRightRadius: tokens.radius.md,
    borderRightWidth: 2,
    borderRightColor: tokens.color.brand.indigo[500],
  },
  handleActive: {
    backgroundColor: "rgba(99, 102, 241, 0.5)",
  },
  handleLine: {
    position: "absolute",
    top: 0,
    bottom: 0,
    width: 2,
    backgroundColor: tokens.color.brand.indigo[500],
  },
  currentIndicator: {
    position: "absolute",
    top: 0,
    bottom: 0,
    width: 2,
    zIndex: 5,
    alignItems: "center",
  },
  currentLine: {
    width: 2,
    height: 72,
    backgroundColor: tokens.color.brand.indigo[300],
    opacity: 0.8,
  },
  totalDuration: {
    fontFamily: tokens.type.scale.caption.family,
    fontSize: tokens.type.scale.caption.size,
    color: tokens.color.text.tertiary,
    textAlign: "center",
  },
});
