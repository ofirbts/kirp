# Design Requirements: UI/UX Modernization & Polishing

Based on the visual reference uploaded by the user, this document establishes the core requirements, tokens, components, and animations needed to elevate the KIRP interface to a premium, high-fidelity standard.

---

## 1. Visual Aesthetics & Design System

### 1.1 Typography
* **Target Font:** `Gilroy` (geometric sans-serif).
* **Open-Source Alternative:** `Outfit` or `Plus Jakarta Sans` from Google Fonts.
* **Usage:**
  * **Headings:** Heavy weights (`font-bold`, `font-extrabold`), tight tracking (`tracking-tight`), large line-heights.
  * **Body:** Clean, legible sans-serif (`font-normal` or `font-medium`), standard tracking.

### 1.2 Color Palette (Harmonious Pastel & Sleek Dark Mode)
We will define custom Tailwind tokens using the following HSL values:
* **Primary / Peach:** `hsl(30, 95%, 72%)` (Soft Warm Peach)
* **Secondary / Teal:** `hsl(165, 55%, 65%)` (Relaxing Mint Teal)
* **Accent / Purple:** `hsl(260, 60%, 75%)` (Lilac Purple)
* **Warm Coral:** `hsl(355, 80%, 75%)` (Salmon Coral)
* **Backgrounds:**
  * **Light Mode:** Soft off-white / light cream (`hsl(210, 20%, 98%)`)
  * **Dark Mode:** Deep slate/navy blue (`hsl(222, 47%, 11%)`)

### 1.3 Glassmorphism & Soft Styling
* **Cards & Panels:** Backdrop filter blur with semi-transparent borders:
  ```css
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  ```
  For dark mode:
  ```css
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  ```
* **Shadows:** Extremely soft, diffuse drop shadows rather than sharp dark borders:
  * `box-shadow: 0px 8px 30px rgba(0, 0, 0, 0.03);`

---

## 2. Interactive Components & Layouts

### 2.1 Mood & Daily Trackers (Mental Health Section)
* **Calendar Strip:** Horizontal scrollable row of dates. Current day highlighted with a pill shape, colored gradient background, and a soft shadow.
* **Circular Progress & Ring Indicators:** Custom SVG circular components showing alignment score (e.g., "67% in a week").
* **Custom Character/Mood Assets:** Soft-edged, expressive emojis (designed or rendered dynamically) matching the warm peach aesthetic.

### 2.2 Table & Operations Grid (Dashboard Section)
* **Device / Item List:** Clean, borderless table lines. Alternating rows or distinct card blocks.
* **Badges:** Soft status capsules (e.g., "Active" in mint teal with 10% opacity background, "Under Maintenance" in warm amber).
* **Toggle Switches:** Custom pill-shaped toggles (`w-11 h-6 bg-slate-200 rounded-full peer-checked:bg-mint`) with smooth transitions.

### 2.3 Stocks & Portfolio Details (Financial Section)
* **Line Charts (Bezier Curves):** Area under the stock curve filled with a fading gradient.
* **Candlestick / Bar Charts:** Green/red volume bars with micro-borders.
* **Buy/Sell Buttons:** Rounded capsules with subtle gradient backgrounds and white bold text.

---

## 3. Motion & Micro-animations (Framer Motion)

### 3.1 Page Transitions & Entry Animations
* All pages and layout panels must perform a stagger-in entry:
  ```javascript
  const containerVariants = {
    hidden: { opacity: 0, y: 15 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 15,
        staggerChildren: 0.08
      }
    }
  };
  ```

### 3.2 Hover & Tap Physics
* **Cards / Buttons:** Bouncy scale-up on hover and scale-down on click:
  ```javascript
  whileHover={{ scale: 1.015 }}
  whileTap={{ scale: 0.985 }}
  ```

### 3.3 Active Tab & Underline Animation
* When switching tabs, the active underline should slide smoothly from one option to another using Framer Motion's `layoutId` attribute to link layouts across states.
