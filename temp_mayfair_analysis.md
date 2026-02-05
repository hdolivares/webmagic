# Mayfair Plumbers - Parallax Issue Analysis

## Problem
Text from hero section moves on top of the next section when scrolling.

## Root Cause
Looking at the CSS:

```css
.hero {
    min-height: 100vh;
    display: flex;
    align-items: center;
    padding: var(--spacing-4xl) var(--spacing-xl);
    background: linear-gradient(...);
    position: relative;
    overflow: hidden; /* ✅ This is correct */
}

.hero::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(...);
    pointer-events: none;
}

.hero-grid {
    max-width: var(--max-width);
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-3xl);
    align-items: center;
    position: relative;
    z-index: 1; /* ✅ Has z-index */
}
```

**Issue**: The hero has `overflow: hidden` but if there's JS-based parallax (scroll-based transform), it might be moving elements outside the hero boundary. The `.hero-grid` has `position: relative; z-index: 1` but this might not be enough if parallax is applied to child elements.

## Solution
1. Ensure hero section has proper containment
2. Add z-index stacking to prevent overlap
3. If parallax exists, constrain it within the hero section
4. Ensure next section has higher z-index to stack above hero

## Fixes to Apply
```css
/* Fix 1: Ensure hero containment */
.hero {
    isolation: isolate; /* Create new stacking context */
    contain: layout style; /* Contain layout calculations */
}

/* Fix 2: Ensure sections stack properly */
.about-section,
.services-section,
.process-section {
    position: relative;
    z-index: 10; /* Higher than hero */
    background: var(--color-surface); /* Ensure opaque background */
}

/* Fix 3: If parallax on hero elements, constrain */
.hero-left,
.hero-right {
    will-change: transform; /* Optimize if animating */
    backface-visibility: hidden; /* Prevent rendering issues */
}
```

## Prevention Guidance for Architect
- Avoid parallax effects that use `position: fixed` or translate outside container
- Always use `isolation: isolate` on hero sections
- Ensure sections have explicit z-index stacking
- Use `contain: layout style` for performance and isolation

