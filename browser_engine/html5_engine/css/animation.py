"""
CSS Animation and Transition handling.
This module provides support for CSS animations and transitions.
"""

import re
import time
from typing import Dict, List, Optional, Tuple, Any, Union, Callable

class KeyframeRule:
    """
    Represents a CSS keyframe rule within an animation.
    """
    def __init__(self, percentage: float, properties: Dict[str, str]):
        """
        Initialize a keyframe rule.
        
        Args:
            percentage: The percentage point in the animation (0-100)
            properties: CSS properties to apply at this keyframe
        """
        self.percentage = percentage
        self.properties = properties
    
    def __repr__(self):
        return f"KeyframeRule({self.percentage}%, {len(self.properties)} properties)"

class Animation:
    """
    Represents a CSS animation.
    """
    def __init__(self, name: str, keyframes: List[KeyframeRule] = None):
        """
        Initialize an animation.
        
        Args:
            name: The animation name
            keyframes: List of keyframe rules
        """
        self.name = name
        self.keyframes = keyframes or []
    
    def add_keyframe(self, keyframe: KeyframeRule) -> None:
        """
        Add a keyframe to the animation.
        
        Args:
            keyframe: The keyframe rule to add
        """
        self.keyframes.append(keyframe)
        # Sort keyframes by percentage
        self.keyframes.sort(key=lambda k: k.percentage)
    
    def get_properties_at_time(self, progress: float) -> Dict[str, str]:
        """
        Get the interpolated CSS properties at a given point in the animation.
        
        Args:
            progress: The animation progress (0-1)
            
        Returns:
            Dictionary of CSS properties interpolated at the current time
        """
        if not self.keyframes:
            return {}
        
        # Convert progress to percentage (0-100)
        percentage = progress * 100
        
        # Find the keyframes to interpolate between
        prev_keyframe = None
        next_keyframe = None
        
        for keyframe in self.keyframes:
            if keyframe.percentage <= percentage:
                prev_keyframe = keyframe
            if keyframe.percentage >= percentage and next_keyframe is None:
                next_keyframe = keyframe
        
        # If no previous keyframe, use the first one
        if prev_keyframe is None and self.keyframes:
            prev_keyframe = self.keyframes[0]
        
        # If no next keyframe, use the last one
        if next_keyframe is None and self.keyframes:
            next_keyframe = self.keyframes[-1]
        
        # If prev and next are the same, just return those properties
        if prev_keyframe == next_keyframe or next_keyframe is None or prev_keyframe is None:
            return prev_keyframe.properties if prev_keyframe else {}
        
        # Calculate interpolation factor
        factor = 0
        if next_keyframe.percentage != prev_keyframe.percentage:
            factor = (percentage - prev_keyframe.percentage) / (next_keyframe.percentage - prev_keyframe.percentage)
        
        # Interpolate between the two keyframes
        result = {}
        
        # Start with all properties from previous keyframe
        for prop, value in prev_keyframe.properties.items():
            result[prop] = value
        
        # Interpolate with properties from next keyframe
        for prop, next_value in next_keyframe.properties.items():
            if prop in result:
                # Property is in both keyframes, interpolate
                prev_value = result[prop]
                result[prop] = self._interpolate_property(prop, prev_value, next_value, factor)
            else:
                # Property is only in next keyframe
                result[prop] = next_value
        
        return result
    
    def _interpolate_property(self, property_name: str, start_value: str, end_value: str, factor: float) -> str:
        """
        Interpolate a CSS property between two values.
        
        Args:
            property_name: The CSS property name
            start_value: The starting value
            end_value: The ending value
            factor: Interpolation factor (0-1)
            
        Returns:
            Interpolated value
        """
        # Handle numeric properties
        if property_name in ('opacity', 'z-index'):
            try:
                start_num = float(start_value)
                end_num = float(end_value)
                result = start_num + factor * (end_num - start_num)
                # Format appropriately for the property
                if property_name == 'z-index':
                    return str(int(result))
                return str(result)
            except ValueError:
                return end_value if factor >= 0.5 else start_value
        
        # Handle length values (e.g., '10px', '2em')
        length_match_start = re.match(r'^([-+]?[0-9]*\.?[0-9]+)([a-z%]*)$', start_value)
        length_match_end = re.match(r'^([-+]?[0-9]*\.?[0-9]+)([a-z%]*)$', end_value)
        
        if length_match_start and length_match_end and length_match_start.group(2) == length_match_end.group(2):
            # Same unit, interpolate the number
            start_num = float(length_match_start.group(1))
            end_num = float(length_match_end.group(1))
            unit = length_match_start.group(2)
            
            result = start_num + factor * (end_num - start_num)
            return f"{result}{unit}"
        
        # Handle color values
        if property_name in ('color', 'background-color', 'border-color'):
            # This is a simplified implementation, a real one would handle all color formats
            # and properly interpolate in an appropriate color space
            return end_value if factor >= 0.5 else start_value
        
        # Default: discrete interpolation (step at 50%)
        return end_value if factor >= 0.5 else start_value

class AnimationInstance:
    """
    Represents a running instance of an animation.
    """
    def __init__(self, animation: Animation, duration: float, timing_function: str = 'linear', 
                 delay: float = 0, iteration_count: Union[int, str] = 1, direction: str = 'normal',
                 fill_mode: str = 'none'):
        """
        Initialize an animation instance.
        
        Args:
            animation: The animation to use
            duration: Duration in seconds
            timing_function: The CSS timing function
            delay: Delay before starting in seconds
            iteration_count: Number of times to run (or 'infinite')
            direction: Direction to run ('normal', 'reverse', 'alternate', 'alternate-reverse')
            fill_mode: Fill mode ('none', 'forwards', 'backwards', 'both')
        """
        self.animation = animation
        self.duration = max(0.001, duration)  # Minimum duration to avoid division by zero
        self.timing_function = timing_function
        self.delay = delay
        
        # Parse iteration count
        if iteration_count == 'infinite':
            self.iteration_count = float('inf')
        else:
            try:
                self.iteration_count = max(0, float(iteration_count))
            except (ValueError, TypeError):
                self.iteration_count = 1
        
        self.direction = direction
        self.fill_mode = fill_mode
        
        # Runtime state
        self.start_time = None
        self.is_running = False
        self.is_paused = False
        self.pause_time = None
        self.elapsed_pause_time = 0
        
    def start(self) -> None:
        """Start the animation."""
        self.start_time = time.time()
        self.is_running = True
        self.is_paused = False
        self.elapsed_pause_time = 0
    
    def pause(self) -> None:
        """Pause the animation."""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self.pause_time = time.time()
    
    def resume(self) -> None:
        """Resume the animation."""
        if self.is_running and self.is_paused:
            self.is_paused = False
            # Add elapsed pause time
            if self.pause_time:
                self.elapsed_pause_time += time.time() - self.pause_time
                self.pause_time = None
    
    def stop(self) -> None:
        """Stop the animation."""
        self.is_running = False
        self.is_paused = False
    
    def get_current_properties(self) -> Dict[str, str]:
        """
        Get the current properties based on animation progress.
        
        Returns:
            Dictionary of current CSS properties
        """
        if not self.is_running or not self.animation.keyframes:
            return {}
        
        # Calculate current time and progress
        if self.is_paused:
            current_time = self.pause_time - self.start_time - self.elapsed_pause_time
        else:
            current_time = time.time() - self.start_time - self.elapsed_pause_time
        
        # Handle delay
        if current_time < self.delay:
            # Animation hasn't started yet
            if self.fill_mode in ('backwards', 'both'):
                # Use properties from first keyframe
                return self.animation.keyframes[0].properties
            return {}
        
        # Adjust for delay
        adjusted_time = current_time - self.delay
        
        # Calculate iteration
        iteration = min(adjusted_time / self.duration, self.iteration_count)
        completed_iterations = int(iteration)
        
        # Check if animation has completed
        if completed_iterations >= self.iteration_count:
            # Animation has completed
            if self.fill_mode in ('forwards', 'both'):
                # Use properties from last keyframe
                return self.animation.keyframes[-1].properties
            return {}
        
        # Calculate progress within current iteration (0-1)
        iteration_progress = iteration - completed_iterations
        
        # Apply direction
        if self.direction == 'reverse':
            progress = 1 - iteration_progress
        elif self.direction == 'alternate':
            if completed_iterations % 2 == 0:
                progress = iteration_progress
            else:
                progress = 1 - iteration_progress
        elif self.direction == 'alternate-reverse':
            if completed_iterations % 2 == 0:
                progress = 1 - iteration_progress
            else:
                progress = iteration_progress
        else:  # normal
            progress = iteration_progress
        
        # Apply timing function
        progress = self._apply_timing_function(progress)
        
        # Get interpolated properties at this progress point
        return self.animation.get_properties_at_time(progress)
    
    def _apply_timing_function(self, progress: float) -> float:
        """
        Apply a CSS timing function to the progress value.
        
        Args:
            progress: The linear progress value (0-1)
            
        Returns:
            Adjusted progress value
        """
        if self.timing_function == 'linear':
            return progress
        
        elif self.timing_function == 'ease':
            # Approximation of the CSS 'ease' function
            # cubic-bezier(0.25, 0.1, 0.25, 1.0)
            return self._cubic_bezier(0.25, 0.1, 0.25, 1.0, progress)
        
        elif self.timing_function == 'ease-in':
            # cubic-bezier(0.42, 0, 1.0, 1.0)
            return self._cubic_bezier(0.42, 0, 1.0, 1.0, progress)
        
        elif self.timing_function == 'ease-out':
            # cubic-bezier(0, 0, 0.58, 1.0)
            return self._cubic_bezier(0, 0, 0.58, 1.0, progress)
        
        elif self.timing_function == 'ease-in-out':
            # cubic-bezier(0.42, 0, 0.58, 1.0)
            return self._cubic_bezier(0.42, 0, 0.58, 1.0, progress)
        
        elif self.timing_function.startswith('cubic-bezier('):
            # Parse cubic-bezier parameters
            match = re.match(r'cubic-bezier\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)', self.timing_function)
            if match:
                x1 = float(match.group(1))
                y1 = float(match.group(2))
                x2 = float(match.group(3))
                y2 = float(match.group(4))
                return self._cubic_bezier(x1, y1, x2, y2, progress)
        
        # Default to linear
        return progress
    
    def _cubic_bezier(self, x1: float, y1: float, x2: float, y2: float, t: float) -> float:
        """
        Calculate a point on a cubic Bezier curve.
        
        Args:
            x1, y1: First control point
            x2, y2: Second control point
            t: Parameter (0-1)
            
        Returns:
            Y value at the given parameter
        """
        # This is a simplified implementation
        # A complete implementation would solve for x and then find the corresponding y
        
        # For now, just approximate by assuming t ~= x, which is not correct
        # but might be good enough for a simple demo
        t_cubed = t * t * t
        t_squared = t * t
        
        y = (1 - t) * (1 - t) * (1 - t) * 0 + \
            3 * (1 - t) * (1 - t) * t * y1 + \
            3 * (1 - t) * t * t * y2 + \
            t * t * t * 1
            
        return y

class Transition:
    """
    Represents a CSS transition.
    """
    def __init__(self, property_name: str, duration: float, timing_function: str = 'linear', delay: float = 0):
        """
        Initialize a transition.
        
        Args:
            property_name: The CSS property to transition
            duration: Duration in seconds
            timing_function: The CSS timing function
            delay: Delay before starting in seconds
        """
        self.property_name = property_name
        self.duration = max(0.001, duration)  # Minimum duration to avoid division by zero
        self.timing_function = timing_function
        self.delay = delay
        
        # Runtime state
        self.start_time = None
        self.is_running = False
        self.start_value = None
        self.end_value = None
    
    def start(self, start_value: str, end_value: str) -> None:
        """
        Start the transition.
        
        Args:
            start_value: The starting CSS property value
            end_value: The ending CSS property value
        """
        self.start_time = time.time()
        self.is_running = True
        self.start_value = start_value
        self.end_value = end_value
    
    def stop(self) -> None:
        """Stop the transition."""
        self.is_running = False
    
    def get_current_value(self) -> Optional[str]:
        """
        Get the current property value based on transition progress.
        
        Returns:
            Current CSS property value or None if transition not running
        """
        if not self.is_running or self.start_value is None or self.end_value is None:
            return None
        
        # Calculate current time and progress
        current_time = time.time() - self.start_time
        
        # Handle delay
        if current_time < self.delay:
            # Transition hasn't started yet
            return self.start_value
        
        # Adjust for delay
        adjusted_time = current_time - self.delay
        
        # Calculate progress (0-1)
        progress = min(adjusted_time / self.duration, 1.0)
        
        # Apply timing function
        progress = self._apply_timing_function(progress)
        
        # Check if transition has completed
        if progress >= 1.0:
            self.is_running = False
            return self.end_value
        
        # Interpolate between start and end values
        return self._interpolate_value(progress)
    
    def _apply_timing_function(self, progress: float) -> float:
        """
        Apply a CSS timing function to the progress value.
        
        Args:
            progress: The linear progress value (0-1)
            
        Returns:
            Adjusted progress value
        """
        # Same implementation as AnimationInstance._apply_timing_function
        if self.timing_function == 'linear':
            return progress
        
        elif self.timing_function == 'ease':
            return self._cubic_bezier(0.25, 0.1, 0.25, 1.0, progress)
        
        elif self.timing_function == 'ease-in':
            return self._cubic_bezier(0.42, 0, 1.0, 1.0, progress)
        
        elif self.timing_function == 'ease-out':
            return self._cubic_bezier(0, 0, 0.58, 1.0, progress)
        
        elif self.timing_function == 'ease-in-out':
            return self._cubic_bezier(0.42, 0, 0.58, 1.0, progress)
        
        elif self.timing_function.startswith('cubic-bezier('):
            match = re.match(r'cubic-bezier\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)', self.timing_function)
            if match:
                x1 = float(match.group(1))
                y1 = float(match.group(2))
                x2 = float(match.group(3))
                y2 = float(match.group(4))
                return self._cubic_bezier(x1, y1, x2, y2, progress)
        
        return progress
    
    def _cubic_bezier(self, x1: float, y1: float, x2: float, y2: float, t: float) -> float:
        """
        Calculate a point on a cubic Bezier curve.
        
        Args:
            x1, y1: First control point
            x2, y2: Second control point
            t: Parameter (0-1)
            
        Returns:
            Y value at the given parameter
        """
        # Same implementation as AnimationInstance._cubic_bezier
        t_cubed = t * t * t
        t_squared = t * t
        
        y = (1 - t) * (1 - t) * (1 - t) * 0 + \
            3 * (1 - t) * (1 - t) * t * y1 + \
            3 * (1 - t) * t * t * y2 + \
            t * t * t * 1
            
        return y
    
    def _interpolate_value(self, progress: float) -> str:
        """
        Interpolate between the start and end values.
        
        Args:
            progress: The interpolation progress (0-1)
            
        Returns:
            Interpolated value
        """
        # Handle numeric properties
        if self.property_name in ('opacity', 'z-index'):
            try:
                start_num = float(self.start_value)
                end_num = float(self.end_value)
                result = start_num + progress * (end_num - start_num)
                # Format appropriately for the property
                if self.property_name == 'z-index':
                    return str(int(result))
                return str(result)
            except ValueError:
                return self.end_value if progress >= 0.5 else self.start_value
        
        # Handle length values (e.g., '10px', '2em')
        length_match_start = re.match(r'^([-+]?[0-9]*\.?[0-9]+)([a-z%]*)$', self.start_value)
        length_match_end = re.match(r'^([-+]?[0-9]*\.?[0-9]+)([a-z%]*)$', self.end_value)
        
        if length_match_start and length_match_end and length_match_start.group(2) == length_match_end.group(2):
            # Same unit, interpolate the number
            start_num = float(length_match_start.group(1))
            end_num = float(length_match_end.group(1))
            unit = length_match_start.group(2)
            
            result = start_num + progress * (end_num - start_num)
            return f"{result}{unit}"
        
        # Handle color values
        if self.property_name in ('color', 'background-color', 'border-color'):
            # This is a simplified implementation, a real one would handle all color formats
            # and properly interpolate in an appropriate color space
            return self.end_value if progress >= 0.5 else self.start_value
        
        # Default: discrete interpolation (step at 50%)
        return self.end_value if progress >= 0.5 else self.start_value

class AnimationManager:
    """
    Manages animations and transitions for HTML elements.
    """
    def __init__(self):
        """Initialize the animation manager."""
        self.animations: Dict[str, Animation] = {}
        self.running_animations: Dict[str, Dict[str, AnimationInstance]] = {}  # element_id -> {name -> instance}
        self.running_transitions: Dict[str, Dict[str, Transition]] = {}  # element_id -> {property -> transition}
        
        # Default animations
        self._init_default_animations()
    
    def _init_default_animations(self) -> None:
        """Initialize default animations."""
        # Fade animations
        fade_in = Animation('fade-in')
        fade_in.add_keyframe(KeyframeRule(0, {'opacity': '0'}))
        fade_in.add_keyframe(KeyframeRule(100, {'opacity': '1'}))
        self.animations['fade-in'] = fade_in
        
        fade_out = Animation('fade-out')
        fade_out.add_keyframe(KeyframeRule(0, {'opacity': '1'}))
        fade_out.add_keyframe(KeyframeRule(100, {'opacity': '0'}))
        self.animations['fade-out'] = fade_out
        
        # Slide animations
        slide_in_right = Animation('slide-in-right')
        slide_in_right.add_keyframe(KeyframeRule(0, {'transform': 'translateX(100%)', 'opacity': '0'}))
        slide_in_right.add_keyframe(KeyframeRule(100, {'transform': 'translateX(0)', 'opacity': '1'}))
        self.animations['slide-in-right'] = slide_in_right
        
        slide_out_right = Animation('slide-out-right')
        slide_out_right.add_keyframe(KeyframeRule(0, {'transform': 'translateX(0)', 'opacity': '1'}))
        slide_out_right.add_keyframe(KeyframeRule(100, {'transform': 'translateX(100%)', 'opacity': '0'}))
        self.animations['slide-out-right'] = slide_out_right
    
    def add_animation(self, animation: Animation) -> None:
        """
        Add an animation definition.
        
        Args:
            animation: The animation to add
        """
        self.animations[animation.name] = animation
    
    def parse_animation(self, element_id: str, animation_str: str) -> None:
        """
        Parse and apply a CSS animation string to an element.
        
        Args:
            element_id: The element ID
            animation_str: The animation property string
        """
        parts = animation_str.split()
        
        # Extract animation parameters
        name = None
        duration = 1.0
        timing_function = 'linear'
        delay = 0
        iteration_count = 1
        direction = 'normal'
        fill_mode = 'none'
        
        for part in parts:
            part = part.strip()
            if part in self.animations:
                name = part
            elif part.endswith('s') and re.match(r'^\d+(\.\d+)?s$', part):
                # Duration or delay
                value = float(part[:-1])
                if delay == 0:
                    duration = value
                else:
                    delay = value
            elif part in ('linear', 'ease', 'ease-in', 'ease-out', 'ease-in-out') or part.startswith('cubic-bezier('):
                timing_function = part
            elif part == 'infinite' or re.match(r'^\d+(\.\d+)?$', part):
                iteration_count = part
            elif part in ('normal', 'reverse', 'alternate', 'alternate-reverse'):
                direction = part
            elif part in ('none', 'forwards', 'backwards', 'both'):
                fill_mode = part
        
        if name and name in self.animations:
            # Create and start the animation
            animation = self.animations[name]
            
            # Initialize element's animations dictionary if needed
            if element_id not in self.running_animations:
                self.running_animations[element_id] = {}
            
            # Create animation instance
            instance = AnimationInstance(
                animation,
                duration=duration,
                timing_function=timing_function,
                delay=delay,
                iteration_count=iteration_count,
                direction=direction,
                fill_mode=fill_mode
            )
            
            # Store and start the animation
            self.running_animations[element_id][name] = instance
            instance.start()
    
    def parse_transition(self, element_id: str, transition_str: str) -> None:
        """
        Parse a CSS transition string and prepare transitions for an element.
        
        Args:
            element_id: The element ID
            transition_str: The transition property string
        """
        parts = transition_str.split(',')
        transitions = []
        
        for part in parts:
            subparts = part.strip().split()
            
            # Extract transition parameters
            property_name = 'all'
            duration = 0
            timing_function = 'linear'
            delay = 0
            
            for subpart in subparts:
                subpart = subpart.strip()
                if subpart.endswith('s') and re.match(r'^\d+(\.\d+)?s$', subpart):
                    # Duration or delay
                    value = float(subpart[:-1])
                    if duration == 0:
                        duration = value
                    else:
                        delay = value
                elif subpart in ('linear', 'ease', 'ease-in', 'ease-out', 'ease-in-out') or subpart.startswith('cubic-bezier('):
                    timing_function = subpart
                elif subpart not in ('all', 'none'):
                    # Assume it's a property name
                    property_name = subpart
            
            # Create the transition
            transition = Transition(
                property_name=property_name,
                duration=duration,
                timing_function=timing_function,
                delay=delay
            )
            
            transitions.append(transition)
        
        # Initialize element's transitions dictionary if needed
        if element_id not in self.running_transitions:
            self.running_transitions[element_id] = {}
        
        # Store transitions (but don't start them yet)
        for transition in transitions:
            self.running_transitions[element_id][transition.property_name] = transition
    
    def start_transition(self, element_id: str, property_name: str, start_value: str, end_value: str) -> None:
        """
        Start a transition for a property.
        
        Args:
            element_id: The element ID
            property_name: The CSS property name
            start_value: The starting value
            end_value: The ending value
        """
        if element_id not in self.running_transitions:
            return
        
        # Check for direct property match
        if property_name in self.running_transitions[element_id]:
            transition = self.running_transitions[element_id][property_name]
            transition.start(start_value, end_value)
        # Check for 'all' transition
        elif 'all' in self.running_transitions[element_id]:
            transition = self.running_transitions[element_id]['all']
            transition.start(start_value, end_value)
    
    def update(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Update all running animations and transitions.
        
        Returns:
            Dictionary mapping element IDs to dictionaries of property changes
        """
        results = {}
        
        # Process animations
        for element_id, animations in list(self.running_animations.items()):
            element_results = {}
            
            for name, instance in list(animations.items()):
                # Get current properties from the animation
                properties = instance.get_current_properties()
                
                # Add to element results
                for prop_name, prop_value in properties.items():
                    element_results[prop_name] = prop_value
                
                # Remove completed animations
                if not instance.is_running:
                    del animations[name]
            
            # Add to results if there are property changes
            if element_results:
                results[element_id] = {'properties': element_results}
            
            # Clean up if no more animations
            if not animations:
                del self.running_animations[element_id]
        
        # Process transitions
        for element_id, transitions in list(self.running_transitions.items()):
            if element_id not in results:
                results[element_id] = {'properties': {}}
            
            for prop_name, transition in list(transitions.items()):
                if transition.is_running:
                    # Get current value from the transition
                    current_value = transition.get_current_value()
                    
                    # Add to element results if there's a value
                    if current_value is not None:
                        results[element_id]['properties'][prop_name] = current_value
                    
                    # Remove completed transitions
                    if not transition.is_running:
                        del transitions[prop_name]
            
            # Clean up if no more transitions
            if not transitions:
                del self.running_transitions[element_id]
        
        return results 