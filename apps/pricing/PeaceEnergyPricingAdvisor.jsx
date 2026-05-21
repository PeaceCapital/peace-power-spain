import { useMemo, useState } from "react";

const PERIODS = [3, 6, 12];

const DEFAULT_TIERS = [
  {
    id: "signal",
    name: "Signal",
    eyebrow: "Briefing layer",
    monthlyPrice: 500,
    priceLabel: "500 / month",
    summary: "Daily PDF market readout for analysts who need signal direction without an operating surface.",
    includes: [],
    bestFor: ["Market analysts", "Internal briefings", "Low-lift evaluation"],
  },
  {
    id: "intelligence",
    name: "Intelligence",
    eyebrow: "Decision layer",
    monthlyPrice: 1500,
    priceLabel: "1,500 / month",
    summary: "Dashboard, archive, and decision support for teams watching OMIE, BESS absorption, and congestion risk.",
    includes: ["Signal"],
    bestFor: ["Research teams", "Advisory desks", "Daily market monitoring"],
  },
  {
    id: "platform",
    name: "Platform",
    eyebrow: "Operating layer",
    monthlyPrice: 3500,
    priceLabel: "3,500 / month",
    summary: "Full technical market monitor with API access, alerts, explainability, and system-ready signal feeds.",
    includes: ["Intelligence"],
    bestFor: ["Trading desks", "Infrastructure funds", "Portfolio operators"],
  },
  {
    id: "execution",
    name: "Execution",
    eyebrow: "Platform add-on",
    monthlyPrice: 2500,
    priceLabel: "2,500 / month",
    summary: "Broker-aware routing, guardrails, and operational controls attached to the Platform tier.",
    includes: ["Platform"],
    bestFor: ["Automated desks", "Broker-connected workflows", "OMS / EMS users"],
    addOn: true,
    attachedTo: "platform",
  },
  {
    id: "advisory",
    name: "Advisory Mandate",
    eyebrow: "Bespoke engagement",
    monthlyPrice: null,
    priceLabel: "Custom scope",
    summary: "Board-level market structure, mandate design, and portfolio advisory where the fee belongs to the thesis.",
    includes: ["Scoped product access"],
    bestFor: ["Board decisions", "Strategic transactions", "Portfolio transformation"],
    custom: true,
  },
];

const PROFILES = [
  {
    id: "analyst",
    label: "Analyst",
    shortLabel: "Analyst",
    recommended: ["intelligence"],
    secondary: ["signal"],
    headline: "Recommended: Intelligence",
    rationale: "The analyst profile needs a daily readout, dashboard context, and enough archive depth to defend a view without carrying execution overhead.",
  },
  {
    id: "desk",
    label: "Trading Desk",
    shortLabel: "Desk",
    recommended: ["platform", "execution"],
    secondary: ["intelligence"],
    headline: "Recommended: Platform + Execution",
    rationale: "A desk needs live signals, API access, alerts, guardrails, and broker connectivity. Anything less is decorative.",
  },
  {
    id: "system",
    label: "Automated System",
    shortLabel: "System",
    recommended: ["platform", "execution"],
    secondary: [],
    headline: "Recommended: Platform + Execution",
    rationale: "Automated workflows need structured outputs, webhooks, routing controls, and audit trails before they should touch live orders.",
  },
  {
    id: "mandate",
    label: "Strategic Mandate",
    shortLabel: "Mandate",
    recommended: ["advisory"],
    secondary: ["platform"],
    headline: "Recommended: Advisory Mandate",
    rationale: "Strategic buyers are not buying access; they are buying judgment, scoping, and a defensible operating thesis.",
  },
];

const BROKERS = [
  { id: "ibkr", label: "IBKR" },
  { id: "fix", label: "FIX-enabled brokers" },
  { id: "omie", label: "OMIE" },
  { id: "xbid", label: "XBID" },
  { id: "emsx", label: "Bloomberg EMSX" },
];

const EXECUTION_CONFIGS = [
  {
    id: "gateway",
    name: "Broker Gateway",
    brokers: ["ibkr", "fix", "emsx"],
    posture: "Best fit for broker-routed discretionary execution.",
  },
  {
    id: "exchange",
    name: "Exchange Routing Pack",
    brokers: ["omie", "xbid", "fix"],
    posture: "Best fit for day-ahead and intraday market workflows.",
  },
  {
    id: "controlled",
    name: "Controlled Automation",
    brokers: ["ibkr", "fix", "omie", "xbid", "emsx"],
    posture: "Best fit when signals, guardrails, and routing must live together.",
  },
];

const FEATURE_ROWS = [
  {
    group: "Briefing",
    rows: [
      {
        feature: "Daily PDF briefing",
        signal: "Daily close",
        intelligence: "Daily close",
        platform: "Daily + intraday",
        execution: "From Platform",
        advisory: "Scoped",
      },
      {
        feature: "Dashboard access",
        signal: false,
        intelligence: "Read-only",
        platform: "Full monitor",
        execution: "Full monitor",
        advisory: "Scoped",
      },
      {
        feature: "Historical market archive",
        signal: "Monthly packet",
        intelligence: "Searchable",
        platform: "Search + export",
        execution: "Search + export",
        advisory: "Custom cut",
      },
      {
        feature: "Market briefing / news overlay",
        signal: "Summary",
        intelligence: "Curated feed",
        platform: "Live context",
        execution: "Live context",
        advisory: "Custom thesis",
      },
    ],
  },
  {
    group: "Signals",
    rows: [
      {
        feature: "OMIE price view",
        signal: "Summary",
        intelligence: "Dashboard",
        platform: "Live + API",
        execution: "Live + API",
        advisory: "Deep dive",
      },
      {
        feature: "Negative price probability",
        signal: "Narrative",
        intelligence: "Score",
        platform: "Score + drivers",
        execution: "Guardrail input",
        advisory: "Scenario work",
      },
      {
        feature: "BESS storage sunset monitor",
        signal: "Monthly",
        intelligence: "Dashboard",
        platform: "Alerted",
        execution: "Guardrail input",
        advisory: "Portfolio thesis",
      },
      {
        feature: "Congestion heatmap",
        signal: false,
        intelligence: "Static view",
        platform: "Live view",
        execution: "Routing input",
        advisory: "Node study",
      },
      {
        feature: "Forecast uncertainty bands",
        signal: false,
        intelligence: "Dashboard",
        platform: "API + dashboard",
        execution: "Sizing input",
        advisory: "Custom model",
      },
    ],
  },
  {
    group: "Workflow",
    rows: [
      {
        feature: "API access",
        signal: false,
        intelligence: false,
        platform: "REST / JSON",
        execution: "REST / JSON",
        advisory: "If scoped",
      },
      {
        feature: "Signal JSON / webhook",
        signal: false,
        intelligence: false,
        platform: "Included",
        execution: "Routable",
        advisory: "If scoped",
      },
      {
        feature: "Automated routing",
        signal: false,
        intelligence: false,
        platform: false,
        execution: "Included",
        advisory: "Design only",
      },
      {
        feature: "Broker connections",
        signal: false,
        intelligence: false,
        platform: false,
        execution: "IBKR / FIX / OMIE / XBID / EMSX",
        advisory: "Architecture",
      },
      {
        feature: "Position guardrails",
        signal: false,
        intelligence: "Policy notes",
        platform: "Rules engine",
        execution: "Pre-trade + post-trade",
        advisory: "Mandate design",
      },
      {
        feature: "Audit log",
        signal: false,
        intelligence: false,
        platform: "Signal log",
        execution: "Signal + order log",
        advisory: "Governance pack",
      },
      {
        feature: "Custom integrations",
        signal: false,
        intelligence: false,
        platform: "Data export",
        execution: "Broker / OMS scope",
        advisory: "Bespoke",
      },
    ],
  },
];

function formatCurrency(value) {
  if (value === null || value === undefined) return "Custom";
  return new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

function getTier(tiers, id) {
  return tiers.find((tier) => tier.id === id);
}

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

function handleRovingKeyDown(event, items, activeId, setActiveId) {
  const currentIndex = items.findIndex((item) => item.id === activeId);
  let nextIndex = currentIndex;

  if (event.key === "ArrowRight" || event.key === "ArrowDown") {
    nextIndex = (currentIndex + 1) % items.length;
  } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
    nextIndex = (currentIndex - 1 + items.length) % items.length;
  } else if (event.key === "Home") {
    nextIndex = 0;
  } else if (event.key === "End") {
    nextIndex = items.length - 1;
  } else {
    return;
  }

  event.preventDefault();
  const nextId = items[nextIndex].id;
  setActiveId(nextId);
  const nextButton = event.currentTarget
    .closest("[data-roving-group]")
    ?.querySelector(`[data-roving-id="${nextId}"]`);
  nextButton?.focus();
}

function ProfileSelector({ activeProfile, setActiveProfile }) {
  return (
    <div className="pe-control-block" aria-labelledby="profile-selector-label">
      <div className="pe-control-topline">
        <span id="profile-selector-label" className="pe-control-label">Usage profile</span>
      </div>
      <div
        className="pe-segmented"
        role="tablist"
        aria-label="Select usage profile"
        data-roving-group
      >
        {PROFILES.map((profile) => (
          <button
            key={profile.id}
            type="button"
            role="tab"
            aria-selected={activeProfile === profile.id}
            aria-controls={`profile-panel-${profile.id}`}
            id={`profile-tab-${profile.id}`}
            tabIndex={activeProfile === profile.id ? 0 : -1}
            data-roving-id={profile.id}
            className={cx("pe-segment", activeProfile === profile.id && "is-active")}
            onClick={() => setActiveProfile(profile.id)}
            onKeyDown={(event) => handleRovingKeyDown(event, PROFILES, activeProfile, setActiveProfile)}
          >
            {profile.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function PeriodSelector({ period, setPeriod }) {
  return (
    <div className="pe-control-block" aria-labelledby="period-selector-label">
      <div className="pe-control-topline">
        <span id="period-selector-label" className="pe-control-label">Cost period</span>
      </div>
      <div
        className="pe-segmented pe-periods"
        role="radiogroup"
        aria-label="Select cost period"
        data-roving-group
      >
        {PERIODS.map((months) => (
          <button
            key={months}
            type="button"
            role="radio"
            aria-checked={period === months}
            tabIndex={period === months ? 0 : -1}
            data-roving-id={String(months)}
            className={cx("pe-segment", period === months && "is-active")}
            onClick={() => setPeriod(months)}
            onKeyDown={(event) => {
              const periodItems = PERIODS.map((value) => ({ id: String(value) }));
              handleRovingKeyDown(event, periodItems, String(period), (value) => setPeriod(Number(value)));
            }}
          >
            {months} months
          </button>
        ))}
      </div>
    </div>
  );
}

function RecommendationPanel({ profile, tiers }) {
  const recommendedNames = profile.recommended
    .map((id) => getTier(tiers, id)?.name)
    .filter(Boolean)
    .join(" + ");

  return (
    <section
      id={`profile-panel-${profile.id}`}
      role="tabpanel"
      aria-labelledby={`profile-tab-${profile.id}`}
      className="pe-recommendation"
    >
      <div>
        <span className="pe-kicker">Recommendation</span>
        <h3>{profile.headline}</h3>
        <p>{profile.rationale}</p>
      </div>
      <div className="pe-recommendation-chip" aria-label={`Recommended tier ${recommendedNames}`}>
        {recommendedNames}
      </div>
    </section>
  );
}

function TierCard({ tier, period, isRecommended, isSecondary, isAttachedTarget }) {
  const periodCost = tier.monthlyPrice === null ? null : tier.monthlyPrice * period;
  const cardLabel = `${tier.name}, ${tier.priceLabel}${isRecommended ? ", recommended" : ""}`;

  return (
    <article
      className={cx(
        "pe-tier-card",
        tier.addOn && "is-addon",
        tier.custom && "is-custom",
        isRecommended && "is-recommended",
        isSecondary && "is-secondary",
        isAttachedTarget && "is-attachment-target",
      )}
      aria-label={cardLabel}
    >
      {isRecommended && <div className="pe-card-badge">Recommended</div>}
      {tier.addOn && <div className="pe-addon-rail" aria-hidden="true" />}
      <div className="pe-card-head">
        <span className="pe-tier-eyebrow">{tier.eyebrow}</span>
        <h3>{tier.name}</h3>
      </div>
      <div className="pe-price">
        {tier.monthlyPrice === null ? (
          <span>{tier.priceLabel}</span>
        ) : (
          <>
            <span>{formatCurrency(tier.monthlyPrice)}</span>
            <small>/ month</small>
          </>
        )}
      </div>
      <p className="pe-tier-summary">{tier.summary}</p>
      <dl className="pe-tier-meta">
        <div>
          <dt>{period} month cost</dt>
          <dd>{periodCost === null ? "Scoped engagement" : formatCurrency(periodCost)}</dd>
        </div>
        <div>
          <dt>Includes</dt>
          <dd>{tier.includes.length ? `Everything in ${tier.includes.join(" + ")}` : "Core tier"}</dd>
        </div>
      </dl>
      <ul className="pe-fit-list" aria-label={`${tier.name} best fit`}>
        {tier.bestFor.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
  );
}

function CostCalculator({ tiers, period }) {
  const platform = getTier(tiers, "platform");
  const execution = getTier(tiers, "execution");
  const combinedMonthly = (platform?.monthlyPrice || 0) + (execution?.monthlyPrice || 0);
  const paidTiers = tiers.filter((tier) => tier.monthlyPrice !== null);

  return (
    <section className="pe-band pe-cost-band" aria-labelledby="cost-calculator-title">
      <div className="pe-band-heading">
        <span className="pe-kicker">Cost calculator</span>
        <h2 id="cost-calculator-title">Total subscription cost</h2>
      </div>
      <div className="pe-cost-grid">
        {paidTiers.map((tier) => (
          <div key={tier.id} className={cx("pe-cost-line", tier.id === "execution" && "is-addon-cost")}>
            <span>{tier.name}</span>
            <strong>{formatCurrency(tier.monthlyPrice * period)}</strong>
            <small>{formatCurrency(tier.monthlyPrice)} monthly</small>
          </div>
        ))}
        <div className="pe-cost-line pe-combined">
          <span>Platform + Execution</span>
          <strong>{formatCurrency(combinedMonthly * period)}</strong>
          <small>{formatCurrency(combinedMonthly)} monthly stack</small>
        </div>
      </div>
    </section>
  );
}

function BrokerMapper({ selectedBroker, setSelectedBroker }) {
  return (
    <section className="pe-band pe-broker-band" aria-labelledby="broker-mapper-title">
      <div className="pe-band-heading">
        <span className="pe-kicker">Execution add-on</span>
        <h2 id="broker-mapper-title">Broker integration mapper</h2>
      </div>
      <div
        className="pe-broker-selector"
        role="radiogroup"
        aria-label="Select broker ecosystem"
        data-roving-group
      >
        {BROKERS.map((broker) => (
          <button
            key={broker.id}
            type="button"
            role="radio"
            aria-checked={selectedBroker === broker.id}
            tabIndex={selectedBroker === broker.id ? 0 : -1}
            data-roving-id={broker.id}
            className={cx("pe-broker-button", selectedBroker === broker.id && "is-active")}
            onClick={() => setSelectedBroker(broker.id)}
            onKeyDown={(event) => handleRovingKeyDown(event, BROKERS, selectedBroker, setSelectedBroker)}
          >
            {broker.label}
          </button>
        ))}
      </div>
      <div className="pe-execution-grid">
        {EXECUTION_CONFIGS.map((config) => {
          const supported = config.brokers.includes(selectedBroker);
          return (
            <article
              key={config.id}
              className={cx("pe-execution-config", supported && "is-supported")}
              aria-label={`${config.name} ${supported ? "supports" : "does not support"} selected broker`}
            >
              <div className="pe-config-top">
                <h3>{config.name}</h3>
                <span>{supported ? "Supported" : "Not primary"}</span>
              </div>
              <p>{config.posture}</p>
              <div className="pe-supported-brokers">
                {config.brokers.map((brokerId) => {
                  const broker = BROKERS.find((item) => item.id === brokerId);
                  return <span key={brokerId}>{broker?.shortLabel || broker?.label || brokerId}</span>;
                })}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function AdvisoryEstimator({ advisoryInputs, setAdvisoryInputs }) {
  const annualAvoidedLoss = Number(advisoryInputs.annualAvoidedLoss) || 0;
  const probability = Number(advisoryInputs.probability) || 0;
  const monthlyMandate = Number(advisoryInputs.monthlyMandate) || 0;
  const months = Number(advisoryInputs.months) || 0;
  const expectedValue = annualAvoidedLoss * (probability / 100);
  const mandateCost = monthlyMandate * months;
  const netValue = expectedValue - mandateCost;
  const roi = mandateCost > 0 ? netValue / mandateCost : 0;

  const updateField = (field, value) => {
    setAdvisoryInputs((current) => ({ ...current, [field]: value }));
  };

  return (
    <section className="pe-band pe-advisory-band" aria-labelledby="advisory-estimator-title">
      <div className="pe-band-heading">
        <span className="pe-kicker">Advisory mandate</span>
        <h2 id="advisory-estimator-title">Bespoke ROI frame</h2>
      </div>
      <div className="pe-advisory-layout">
        <div className="pe-input-grid">
          <label>
            <span>Annual exposure at risk</span>
            <input
              type="number"
              inputMode="numeric"
              min="0"
              step="25000"
              value={advisoryInputs.annualAvoidedLoss}
              onChange={(event) => updateField("annualAvoidedLoss", event.target.value)}
            />
          </label>
          <label>
            <span>Capture probability (%)</span>
            <input
              type="number"
              inputMode="numeric"
              min="0"
              max="100"
              step="5"
              value={advisoryInputs.probability}
              onChange={(event) => updateField("probability", event.target.value)}
            />
          </label>
          <label>
            <span>Indicative monthly mandate</span>
            <input
              type="number"
              inputMode="numeric"
              min="0"
              step="1000"
              value={advisoryInputs.monthlyMandate}
              onChange={(event) => updateField("monthlyMandate", event.target.value)}
            />
          </label>
          <label>
            <span>Mandate length</span>
            <select
              value={advisoryInputs.months}
              onChange={(event) => updateField("months", event.target.value)}
            >
              <option value="3">3 months</option>
              <option value="6">6 months</option>
              <option value="12">12 months</option>
            </select>
          </label>
        </div>
        <div className="pe-roi-output" aria-live="polite">
          <div>
            <span>Expected value</span>
            <strong>{formatCurrency(expectedValue)}</strong>
          </div>
          <div>
            <span>Mandate cost</span>
            <strong>{formatCurrency(mandateCost)}</strong>
          </div>
          <div className={cx("pe-roi-net", netValue >= 0 ? "is-positive" : "is-negative")}>
            <span>Indicative net ROI</span>
            <strong>{mandateCost > 0 ? `${(roi * 100).toFixed(0)}%` : "Scoped"}</strong>
          </div>
          <p>
            This is not a canned price. It is a scoping frame for deciding whether
            the mandate is economically worth a serious conversation.
          </p>
        </div>
      </div>
    </section>
  );
}

function FeatureValue({ value }) {
  if (value === false || value === null || value === undefined) {
    return <span className="pe-feature-no" aria-label="Not included">-</span>;
  }

  if (value === true) {
    return <span className="pe-feature-yes" aria-label="Included">Included</span>;
  }

  return <span>{value}</span>;
}

function FeatureMatrix({ tiers }) {
  return (
    <section className="pe-band pe-feature-band" aria-labelledby="feature-matrix-title">
      <div className="pe-band-heading">
        <span className="pe-kicker">Feature matrix</span>
        <h2 id="feature-matrix-title">Capability inheritance by tier</h2>
      </div>
      <div className="pe-table-scroll" tabIndex="0" aria-label="Scrollable feature comparison table">
        <table className="pe-feature-table">
          <caption>Peace Energy pricing feature matrix</caption>
          <thead>
            <tr>
              <th scope="col">Capability</th>
              {tiers.map((tier) => (
                <th key={tier.id} scope="col">
                  <span>{tier.name}</span>
                  {tier.includes.length > 0 && <small>Includes {tier.includes.join(" + ")}</small>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FEATURE_ROWS.flatMap((section) => [
              <tr key={section.group} className="pe-feature-group">
                <th scope="row" colSpan={tiers.length + 1}>{section.group}</th>
              </tr>,
              ...section.rows.map((row) => (
                <tr key={`${section.group}-${row.feature}`}>
                  <th scope="row">{row.feature}</th>
                  {tiers.map((tier) => (
                    <td key={tier.id}>
                      <FeatureValue value={row[tier.id]} />
                    </td>
                  ))}
                </tr>
              )),
            ])}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function PeaceEnergyPricingAdvisor({ tiers = DEFAULT_TIERS }) {
  const [activeProfile, setActiveProfile] = useState(PROFILES[0].id);
  const [period, setPeriod] = useState(6);
  const [selectedBroker, setSelectedBroker] = useState(BROKERS[0].id);
  const [advisoryInputs, setAdvisoryInputs] = useState({
    annualAvoidedLoss: 250000,
    probability: 35,
    monthlyMandate: 12000,
    months: 6,
  });

  const profile = useMemo(
    () => PROFILES.find((item) => item.id === activeProfile) || PROFILES[0],
    [activeProfile],
  );

  const recommendedSet = useMemo(() => new Set(profile.recommended), [profile]);
  const secondarySet = useMemo(() => new Set(profile.secondary), [profile]);

  return (
    <>
      <style>{`
        .peace-pricing-advisor {
          --pe-navy: #07111f;
          --pe-navy-2: #0b1829;
          --pe-navy-3: #102238;
          --pe-text: #f4f8fb;
          --pe-text-2: #c8d6e3;
          --pe-text-3: #8ea1b3;
          --pe-rule: rgba(159, 192, 214, 0.18);
          --pe-rule-2: rgba(159, 192, 214, 0.28);
          --pe-teal: #2ee6c8;
          --pe-blue: #1a9fc2;
          --pe-warn: #d7b85b;
          --pe-danger: #e87474;
          --pe-gradient: linear-gradient(135deg, var(--pe-blue), var(--pe-teal));
          background: var(--pe-navy);
          color: var(--pe-text);
          font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
          font-weight: 300;
          min-height: 100%;
          padding: 56px 24px 72px;
        }

        .peace-pricing-advisor *,
        .peace-pricing-advisor *::before,
        .peace-pricing-advisor *::after {
          box-sizing: border-box;
        }

        .pe-shell {
          width: min(1380px, 100%);
          margin: 0 auto;
        }

        .pe-heading {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 24px;
          align-items: end;
          padding-bottom: 24px;
          border-bottom: 1px solid var(--pe-rule);
        }

        .pe-kicker,
        .pe-control-label,
        .pe-tier-eyebrow,
        .pe-card-badge,
        .pe-cost-line small,
        .pe-config-top span {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }

        .pe-kicker,
        .pe-tier-eyebrow {
          color: var(--pe-teal);
        }

        .pe-heading h1,
        .pe-band-heading h2,
        .pe-card-head h3,
        .pe-recommendation h3,
        .pe-execution-config h3 {
          font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
          font-weight: 700;
          letter-spacing: 0;
          margin: 0;
        }

        .pe-heading h1 {
          max-width: 840px;
          margin-top: 10px;
          font-size: clamp(34px, 5vw, 68px);
          line-height: 0.96;
        }

        .pe-heading p {
          max-width: 760px;
          margin: 18px 0 0;
          color: var(--pe-text-2);
          font-size: 17px;
          line-height: 1.65;
        }

        .pe-heading-metric {
          display: grid;
          gap: 4px;
          min-width: 180px;
          padding: 18px;
          border: 1px solid var(--pe-rule-2);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.03);
        }

        .pe-heading-metric span {
          color: var(--pe-text-3);
          font-size: 12px;
        }

        .pe-heading-metric strong {
          font-size: 26px;
          line-height: 1;
        }

        .pe-controls {
          display: grid;
          grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
          gap: 18px;
          margin-top: 24px;
        }

        .pe-control-block {
          min-width: 0;
        }

        .pe-control-topline {
          margin-bottom: 10px;
        }

        .pe-control-label {
          color: var(--pe-text-3);
        }

        .pe-segmented,
        .pe-broker-selector {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .pe-segment,
        .pe-broker-button {
          appearance: none;
          border: 1px solid var(--pe-rule-2);
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.04);
          color: var(--pe-text-2);
          cursor: pointer;
          font: inherit;
          font-weight: 700;
          min-height: 42px;
          padding: 10px 15px;
          transition: border-color 160ms ease, color 160ms ease, background 160ms ease, transform 160ms ease;
        }

        .pe-segment:hover,
        .pe-broker-button:hover {
          border-color: rgba(46, 230, 200, 0.65);
          color: var(--pe-text);
          transform: translateY(-1px);
        }

        .pe-segment.is-active,
        .pe-broker-button.is-active {
          background: var(--pe-gradient);
          border-color: transparent;
          color: #05101d;
        }

        .peace-pricing-advisor button:focus-visible,
        .peace-pricing-advisor input:focus-visible,
        .peace-pricing-advisor select:focus-visible,
        .pe-table-scroll:focus-visible {
          outline: 3px solid rgba(46, 230, 200, 0.7);
          outline-offset: 3px;
        }

        .pe-recommendation {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 20px;
          align-items: center;
          margin-top: 28px;
          padding: 22px;
          border: 1px solid rgba(46, 230, 200, 0.38);
          border-radius: 8px;
          background:
            linear-gradient(135deg, rgba(26, 159, 194, 0.14), rgba(46, 230, 200, 0.08)),
            rgba(255, 255, 255, 0.03);
        }

        .pe-recommendation h3 {
          margin-top: 6px;
          font-size: clamp(22px, 3vw, 34px);
        }

        .pe-recommendation p {
          max-width: 820px;
          margin: 10px 0 0;
          color: var(--pe-text-2);
          line-height: 1.6;
        }

        .pe-recommendation-chip {
          align-self: stretch;
          display: grid;
          place-items: center;
          min-width: 230px;
          padding: 18px;
          border-radius: 8px;
          background: rgba(7, 17, 31, 0.7);
          color: var(--pe-teal);
          font-weight: 700;
          text-align: center;
        }

        .pe-tier-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 14px;
          margin-top: 24px;
          align-items: stretch;
        }

        .pe-tier-card {
          position: relative;
          display: flex;
          flex-direction: column;
          min-width: 0;
          min-height: 460px;
          padding: 20px;
          border: 1px solid var(--pe-rule);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.035);
          overflow: hidden;
          transition: border-color 180ms ease, transform 180ms ease, background 180ms ease;
        }

        .pe-tier-card.is-recommended {
          border-color: rgba(46, 230, 200, 0.75);
          background:
            linear-gradient(180deg, rgba(26, 159, 194, 0.16), rgba(46, 230, 200, 0.05)),
            rgba(255, 255, 255, 0.045);
          transform: translateY(-4px);
        }

        .pe-tier-card.is-secondary {
          border-color: rgba(46, 230, 200, 0.32);
        }

        .pe-tier-card.is-addon {
          border-style: dashed;
          background: rgba(16, 34, 56, 0.58);
        }

        .pe-tier-card.is-addon::before {
          content: "";
          position: absolute;
          top: 28px;
          left: -18px;
          width: 18px;
          height: 2px;
          background: var(--pe-gradient);
        }

        .pe-addon-rail {
          position: absolute;
          inset: 0 auto 0 0;
          width: 4px;
          background: var(--pe-gradient);
        }

        .pe-card-badge {
          align-self: flex-start;
          margin-bottom: 14px;
          padding: 6px 9px;
          border-radius: 999px;
          background: var(--pe-gradient);
          color: #05101d;
        }

        .pe-card-head h3 {
          margin-top: 6px;
          font-size: 26px;
        }

        .pe-price {
          min-height: 58px;
          margin-top: 18px;
          display: flex;
          align-items: baseline;
          gap: 8px;
          flex-wrap: wrap;
        }

        .pe-price span {
          font-size: clamp(25px, 2.4vw, 36px);
          font-weight: 700;
          letter-spacing: 0;
        }

        .pe-price small {
          color: var(--pe-text-3);
          font-size: 13px;
        }

        .pe-tier-summary {
          color: var(--pe-text-2);
          line-height: 1.55;
          margin: 10px 0 0;
          min-height: 100px;
        }

        .pe-tier-meta {
          display: grid;
          gap: 10px;
          margin: 18px 0 0;
          padding-top: 16px;
          border-top: 1px solid var(--pe-rule);
        }

        .pe-tier-meta div {
          display: grid;
          gap: 3px;
        }

        .pe-tier-meta dt {
          color: var(--pe-text-3);
          font-size: 12px;
        }

        .pe-tier-meta dd {
          margin: 0;
          color: var(--pe-text);
          font-weight: 700;
          line-height: 1.35;
        }

        .pe-fit-list {
          display: grid;
          gap: 8px;
          margin: auto 0 0;
          padding: 18px 0 0;
          list-style: none;
        }

        .pe-fit-list li {
          position: relative;
          padding-left: 16px;
          color: var(--pe-text-2);
          font-size: 13px;
          line-height: 1.35;
        }

        .pe-fit-list li::before {
          content: "";
          position: absolute;
          left: 0;
          top: 0.58em;
          width: 6px;
          height: 6px;
          border-radius: 999px;
          background: var(--pe-teal);
        }

        .pe-band {
          margin-top: 34px;
          padding-top: 28px;
          border-top: 1px solid var(--pe-rule);
        }

        .pe-band-heading {
          display: grid;
          gap: 6px;
          margin-bottom: 18px;
        }

        .pe-band-heading h2 {
          font-size: clamp(24px, 3vw, 38px);
        }

        .pe-cost-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 12px;
        }

        .pe-cost-line {
          display: grid;
          gap: 7px;
          min-height: 130px;
          padding: 16px;
          border: 1px solid var(--pe-rule);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.035);
        }

        .pe-cost-line span {
          color: var(--pe-text-2);
        }

        .pe-cost-line strong {
          align-self: end;
          font-size: clamp(22px, 2.2vw, 34px);
        }

        .pe-cost-line small {
          color: var(--pe-text-3);
        }

        .pe-combined {
          border-color: rgba(46, 230, 200, 0.62);
          background: linear-gradient(135deg, rgba(26, 159, 194, 0.16), rgba(46, 230, 200, 0.07));
        }

        .pe-broker-selector {
          margin-bottom: 16px;
        }

        .pe-execution-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
        }

        .pe-execution-config {
          padding: 18px;
          border: 1px solid var(--pe-rule);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.035);
        }

        .pe-execution-config.is-supported {
          border-color: rgba(46, 230, 200, 0.7);
          background: rgba(46, 230, 200, 0.07);
        }

        .pe-config-top {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          align-items: start;
        }

        .pe-config-top h3 {
          font-size: 19px;
        }

        .pe-config-top span {
          color: var(--pe-teal);
          white-space: nowrap;
        }

        .pe-execution-config p {
          color: var(--pe-text-2);
          line-height: 1.55;
          margin: 12px 0 0;
        }

        .pe-supported-brokers {
          display: flex;
          flex-wrap: wrap;
          gap: 7px;
          margin-top: 14px;
        }

        .pe-supported-brokers span {
          padding: 5px 8px;
          border: 1px solid var(--pe-rule);
          border-radius: 999px;
          color: var(--pe-text-3);
          font-size: 12px;
        }

        .pe-advisory-layout {
          display: grid;
          grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
          gap: 18px;
          align-items: stretch;
        }

        .pe-input-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }

        .pe-input-grid label {
          display: grid;
          gap: 8px;
          color: var(--pe-text-2);
          font-size: 13px;
        }

        .pe-input-grid input,
        .pe-input-grid select {
          width: 100%;
          min-height: 46px;
          border: 1px solid var(--pe-rule-2);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.04);
          color: var(--pe-text);
          font: inherit;
          font-weight: 700;
          padding: 10px 12px;
        }

        .pe-input-grid select option {
          background: var(--pe-navy);
          color: var(--pe-text);
        }

        .pe-roi-output {
          display: grid;
          gap: 12px;
          padding: 18px;
          border: 1px solid rgba(46, 230, 200, 0.38);
          border-radius: 8px;
          background: rgba(46, 230, 200, 0.06);
        }

        .pe-roi-output div {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: baseline;
          padding-bottom: 10px;
          border-bottom: 1px solid var(--pe-rule);
        }

        .pe-roi-output span {
          color: var(--pe-text-2);
        }

        .pe-roi-output strong {
          font-size: 24px;
        }

        .pe-roi-net.is-positive strong {
          color: var(--pe-teal);
        }

        .pe-roi-net.is-negative strong {
          color: var(--pe-danger);
        }

        .pe-roi-output p {
          margin: 0;
          color: var(--pe-text-3);
          line-height: 1.55;
        }

        .pe-table-scroll {
          overflow-x: auto;
          border: 1px solid var(--pe-rule);
          border-radius: 8px;
        }

        .pe-feature-table {
          width: 100%;
          min-width: 1020px;
          border-collapse: collapse;
          background: rgba(255, 255, 255, 0.025);
        }

        .pe-feature-table caption {
          position: absolute;
          width: 1px;
          height: 1px;
          overflow: hidden;
          clip: rect(0 0 0 0);
        }

        .pe-feature-table th,
        .pe-feature-table td {
          padding: 14px 16px;
          border-bottom: 1px solid var(--pe-rule);
          text-align: left;
          vertical-align: top;
        }

        .pe-feature-table thead th {
          position: sticky;
          top: 0;
          z-index: 1;
          background: var(--pe-navy-2);
          color: var(--pe-text);
          font-weight: 700;
        }

        .pe-feature-table thead th:first-child {
          min-width: 220px;
        }

        .pe-feature-table thead small {
          display: block;
          margin-top: 5px;
          color: var(--pe-teal);
          font-size: 11px;
          font-weight: 300;
        }

        .pe-feature-table tbody th {
          color: var(--pe-text);
          font-weight: 700;
        }

        .pe-feature-table tbody td {
          color: var(--pe-text-2);
          line-height: 1.45;
        }

        .pe-feature-group th {
          background: rgba(46, 230, 200, 0.08);
          color: var(--pe-teal);
          font-size: 12px;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }

        .pe-feature-no {
          color: var(--pe-text-3);
        }

        .pe-feature-yes {
          color: var(--pe-teal);
          font-weight: 700;
        }

        @media (max-width: 1180px) {
          .pe-tier-grid,
          .pe-cost-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .pe-tier-card.is-addon::before {
            display: none;
          }
        }

        @media (max-width: 860px) {
          .peace-pricing-advisor {
            padding: 36px 16px 52px;
          }

          .pe-heading,
          .pe-controls,
          .pe-recommendation,
          .pe-advisory-layout {
            grid-template-columns: 1fr;
          }

          .pe-heading-metric,
          .pe-recommendation-chip {
            min-width: 0;
          }

          .pe-execution-grid,
          .pe-input-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 620px) {
          .pe-tier-grid,
          .pe-cost-grid {
            grid-template-columns: 1fr;
          }

          .pe-tier-card {
            min-height: auto;
          }

          .pe-tier-summary {
            min-height: 0;
          }

          .pe-segment,
          .pe-broker-button {
            flex: 1 1 auto;
            justify-content: center;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          .peace-pricing-advisor *,
          .peace-pricing-advisor *::before,
          .peace-pricing-advisor *::after {
            scroll-behavior: auto !important;
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
          }
        }
      `}</style>

      <section className="peace-pricing-advisor" aria-labelledby="peace-pricing-advisor-title">
        <div className="pe-shell">
          <header className="pe-heading">
            <div>
              <span className="pe-kicker">Peace Energy pricing</span>
              <h1 id="peace-pricing-advisor-title">Choose the tier that matches your workflow.</h1>
              <p>
                A pricing comparison and recommendation engine for prospects who
                need to see cost, capability, and broker fit without wading through
                a generic enterprise pricing page.
              </p>
            </div>
            <div className="pe-heading-metric">
              <span>Selected profile</span>
              <strong>{profile.shortLabel}</strong>
            </div>
          </header>

          <div className="pe-controls" aria-label="Pricing advisor controls">
            <ProfileSelector activeProfile={activeProfile} setActiveProfile={setActiveProfile} />
            <PeriodSelector period={period} setPeriod={setPeriod} />
          </div>

          <RecommendationPanel profile={profile} tiers={tiers} />

          <section className="pe-tier-grid" aria-label="Peace Energy service tiers">
            {tiers.map((tier) => (
              <TierCard
                key={tier.id}
                tier={tier}
                period={period}
                isRecommended={recommendedSet.has(tier.id)}
                isSecondary={secondarySet.has(tier.id)}
                isAttachedTarget={tiers.some((item) => item.attachedTo === tier.id)}
              />
            ))}
          </section>

          <CostCalculator tiers={tiers} period={period} />
          <BrokerMapper selectedBroker={selectedBroker} setSelectedBroker={setSelectedBroker} />
          <AdvisoryEstimator advisoryInputs={advisoryInputs} setAdvisoryInputs={setAdvisoryInputs} />
          <FeatureMatrix tiers={tiers} />
        </div>
      </section>
    </>
  );
}

export { DEFAULT_TIERS, PROFILES, BROKERS, EXECUTION_CONFIGS, FEATURE_ROWS };
