import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'FreightFlow — Case Study',
}

const SECTIONS = [
  {
    id: 'introduction',
    label: 'Introduction',
    paragraphs: [
      'I wanted to understand how supply chains work, specifically in the geographic dimension: which regions feed which industries, and how fragile those connections are. The U.S. federal government publishes detailed records of every major freight flow across the country in a 2 million row spreadsheet. I built a tool to make it explorable: pick a finished product, see where its raw materials come from, how concentrated those sources are, and what happens if a key region goes offline.',
      'The app lets you pick between 4 diverse supply chains tracked to a primary US assembly hub: automobiles, beef, pharmaceuticals, and steel. For each product, you can explore which raw materials feed it, where they originate geographically, and what share of total input each source zone contributes. You can also simulate disruptions: select one or more source zones and see the resulting tonnage gap and estimated cost impact. A separate view identifies the most systemically critical source zones, whose disruption would ripple across multiple supply chains simultaneously.',
    ],
  },
  {
    id: 'methodology',
    label: 'Data & Methodology',
    paragraphs: [
      'The data comes from the Freight Analysis Framework (FAF5 v5.7.1), published by the Bureau of Transportation Statistics and the Federal Highway Administration. FAF5 covers domestic freight flows between 132 geographic zones across the US, with records for commodity type, transport mode, origin, destination, tonnage, and value. The dataset contains 522,000 domestic flow records for 2022.',
      'To model each supply chain, I identified the key precursor commodity types for each finished product and pulled the corresponding FAF5 freight flows into the headline assembly zone. For automobiles, the relevant commodity categories — base metals, plastics and rubber, electronics, chemicals, and glass — were selected based on material composition data from the American Chemistry Council\'s Chemistry and Automobiles: Driving the Future (2024). For pharmaceuticals, no equivalent public source exists; drug formulations are proprietary and vary widely by product, so the precursor categories used are rough approximations based on general industry knowledge. The geographic flow patterns shown are real FAF5 data; the commodity selection for pharmaceuticals should be understood as illustrative rather than precise.',
      'Concentration risk is calculated as the percentage of a product\'s primary precursor tonnage that flows into the headline assembly zone from just the top three source zones. A high percentage means a small number of regions are responsible for the majority of supply, indicating fragility.',
      'The Critical Nodes score takes a broader view. Rather than looking at one supply chain in isolation, it measures what share of total modelled precursor tonnage across all four supply chains a given source zone supplies. A zone that feeds multiple supply chains in large quantities scores higher. Intra-zone flows are excluded from this calculation, because those flows don\'t represent a genuine external dependency and would artificially inflate scores for large industrial zones.',
      'Two of the four supply chains warrant a note on scope. Beef is modelled as a raw commodity rather than a manufactured product; the analysis tracks where beef is produced and shipped from, not upstream feed or agricultural inputs. Steel is treated as a precursor material in its own right: the app tracks flows of base metal into the automobile assembly zone rather than modelling the steelmaking process itself. These are intentional simplifications — the FAF5 commodity codes align more cleanly with these materials as freight categories, and the geographic concentration story is more meaningful at the level of where the material ships from.',
    ],
  },
]

const DECISIONS = [
  {
    title: 'Static pre-computed data over a live backend',
    body: 'Rather than running a database and API server at runtime, all supply chain analysis is pre-computed into static JSON files that the frontend loads directly. This means the app runs for free on Vercel with no infrastructure to maintain, loads instantly, and has no moving parts that can fail. The tradeoff is that updating the data requires re-running the precompute script, which is acceptable for a dataset that updates annually.',
  },
  {
    title: 'Aggregating FAF5 metro zones',
    body: 'FAF5 splits some metro areas across state lines; Chicago, for example, appears as separate Illinois and Indiana zones. Left uncorrected, this made Chicago show up as two different assembly locations. The solution was to remap those zone IDs to a single "Chicago Metro" entry before processing, which produces a more accurate and readable result.',
  },
  {
    title: 'Excluding intra-zone flows from Critical Nodes',
    body: 'When calculating which source zones pose the greatest systemic risk, flows where a zone supplies itself were excluded. Without this, large industrial zones like Detroit would appear as top critical nodes simply because they consume their own output — which isn\'t a supply chain vulnerability.',
  },
]

const NEXT_STEPS = [
  {
    title: 'Source better BOM data for pharmaceuticals',
    body: 'The pharmaceutical precursor categories are rough approximations. Ideally these would be grounded in a published source the way the automobile inputs are grounded in ACC material composition data. No clean public source currently exists for this, but FDA API sourcing reports or academic literature on drug manufacturing inputs could improve it.',
  },
  {
    title: 'Improve the disruption model',
    body: 'The current simulator calculates a simple tonnage gap when a zone goes offline. A more realistic model would account for partial substitution — the ability of other source zones to absorb some of the shortfall — and would model lead times and inventory buffers. This would move the simulator from illustrative to genuinely analytical.',
  },
  {
    title: 'Mode-level breakdown on the map',
    body: 'FAF5 records transport mode: truck, rail, water, pipeline. Visualizing which corridors are truck-dependent versus rail-dependent would add another dimension to the fragility analysis, since mode concentration is itself a vulnerability.',
  },
]

export default function CaseStudyPage() {
  return (
    <div className="h-full overflow-y-auto">
    <div className="mx-auto max-w-3xl px-6 py-16">

      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-primary">
        FreightFlow
      </p>
      <h1 className="mb-2 text-4xl font-extrabold tracking-tight">Case Study</h1>
      <p className="mb-12 text-sm text-muted-foreground">
        How and why it was built — data sources, methodology, and design decisions.
      </p>

      <div className="space-y-14 text-sm leading-relaxed text-muted-foreground">

        {/* Introduction + Methodology */}
        {SECTIONS.map(section => (
          <section key={section.id}>
            <h2 className="mb-5 text-lg font-bold text-foreground">{section.label}</h2>
            <div className="space-y-4">
              {section.paragraphs.map((p, i) => <p key={i}>{p}</p>)}
            </div>
          </section>
        ))}

        {/* Key Technical Decisions */}
        <section>
          <h2 className="mb-5 text-lg font-bold text-foreground">Key Technical Decisions</h2>
          <div className="space-y-6">
            {DECISIONS.map(({ title, body }) => (
              <div key={title} className="rounded-lg border border-border bg-card p-5">
                <p className="mb-2 font-semibold text-foreground">{title}</p>
                <p>{body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Next Steps */}
        <section>
          <h2 className="mb-5 text-lg font-bold text-foreground">What I&apos;d Do Differently / Next Steps</h2>
          <div className="space-y-6">
            {NEXT_STEPS.map(({ title, body }) => (
              <div key={title} className="rounded-lg border border-border bg-card p-5">
                <p className="mb-2 font-semibold text-foreground">{title}</p>
                <p>{body}</p>
              </div>
            ))}
          </div>
        </section>

          </div>
    </div>
    </div>
  )
}
