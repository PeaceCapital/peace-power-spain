# Peace Energy Pricing Advisor

Self-contained React component for the Peace Energy pricing page.

```jsx
import { PeaceEnergyPricingAdvisor } from "./apps/pricing";

export default function PricingPage() {
  return <PeaceEnergyPricingAdvisor />;
}
```

The component ships with default tier data:

- Signal: EUR 500 / month
- Intelligence: EUR 1,500 / month
- Platform: EUR 3,500 / month, modeled as an assumption
- Execution: EUR 2,500 / month, modeled as a Platform add-on
- Advisory Mandate: custom scope with an ROI estimator

Override `tiers` when the final production pricing source differs:

```jsx
<PeaceEnergyPricingAdvisor tiers={customPeaceEnergyTiers} />
```

It includes profile-based recommendations, 3 / 6 / 12 month cost calculations,
broker ecosystem mapping, advisory ROI framing, mobile horizontal matrix
scrolling, keyboard navigation, and ARIA labels.
