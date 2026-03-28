'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'
import {
  Github,
  Linkedin,
  Mail,
  ExternalLink,
  FileDown,
  Truck,
  BarChart2,
  Map,
  Database,
  ChevronRight,
} from 'lucide-react'

// ─── Data ────────────────────────────────────────────────────────────────────

const LINKS = {
  github:      'https://github.com/placeholder',
  linkedin:    'https://linkedin.com/in/placeholder',
  email:       'mailto:placeholder@email.com',
  resume:      '/resume.pdf',
  freightflow: 'https://github.com/placeholder/freightflow',
}

const TECH_BADGES = [
  'Next.js 14', 'TypeScript', 'Python',
  'PostgreSQL', 'Leaflet', 'Recharts', 'Tailwind CSS', 'Docker', 'Vercel',
]

const SKILLS = [
  { category: 'Frontend',  items: ['React / Next.js', 'TypeScript', 'Tailwind CSS', 'Data Visualization'] },
  { category: 'Backend',   items: ['Python', 'PostgreSQL', 'REST APIs', 'ETL Pipelines'] },
  { category: 'Tools',     items: ['Docker', 'Git', 'Vercel', 'Linux'] },
  { category: 'Concepts',  items: ['Supply Chain Analysis', 'Geospatial Data', 'Cost Modelling', 'FAF5 / BTS Data'] },
]

const FREIGHTFLOW_FEATURES = [
  { icon: Map,       label: 'Interactive Map',    desc: 'Weighted freight-flow lines across US corridors' },
  { icon: BarChart2, label: 'Concentration Risk', desc: 'Top-3 supplier concentration scored across 4 supply chains' },
  { icon: Database,  label: 'FAF5 Data',          desc: '522k freight flow records from BTS/FHWA (2022)' },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

function TechBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-sky-500/25 bg-sky-500/8 px-3 py-1 text-xs font-medium text-sky-300">
      {label}
    </span>
  )
}

function SkillGroup({ category, items }: { category: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-800/50 p-5">
      <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">{category}</p>
      <ul className="space-y-1.5">
        {items.map(item => (
          <li key={item} className="flex items-center gap-2 text-sm text-slate-300">
            <span className="h-1 w-1 shrink-0 rounded-full bg-sky-400/60" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PortfolioPage() {
  useEffect(() => { document.title = '[Your Name] — Portfolio' }, [])

  const projectsRef = useRef<HTMLElement>(null)
  const aboutRef    = useRef<HTMLElement>(null)
  const resumeRef   = useRef<HTMLElement>(null)

  function scrollTo(ref: React.RefObject<HTMLElement | null>) {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-100">

      {/* ── Sticky Nav ──────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-slate-700/50 bg-[#0f172a]/90 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <span className="text-sm font-bold tracking-tight text-white">[Your Name]</span>

          <nav className="hidden items-center gap-6 sm:flex">
            <button onClick={() => scrollTo(projectsRef)}
              className="text-sm text-slate-400 transition-colors hover:text-white">
              Projects
            </button>
            <button onClick={() => scrollTo(aboutRef)}
              className="text-sm text-slate-400 transition-colors hover:text-white">
              About
            </button>
            <button onClick={() => scrollTo(resumeRef)}
              className="text-sm text-slate-400 transition-colors hover:text-white">
              Resume
            </button>
          </nav>

          <div className="flex items-center gap-1">
            <a href={LINKS.github} target="_blank" rel="noopener noreferrer"
              className="rounded-md p-2 text-slate-400 transition-colors hover:bg-slate-700/60 hover:text-white">
              <Github className="h-4 w-4" />
            </a>
            <a href={LINKS.linkedin} target="_blank" rel="noopener noreferrer"
              className="rounded-md p-2 text-slate-400 transition-colors hover:bg-slate-700/60 hover:text-white">
              <Linkedin className="h-4 w-4" />
            </a>
            <a href={LINKS.email}
              className="rounded-md p-2 text-slate-400 transition-colors hover:bg-slate-700/60 hover:text-white">
              <Mail className="h-4 w-4" />
            </a>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6">

        {/* ── Hero ──────────────────────────────────────────────────────── */}
        <section className="flex min-h-[80vh] flex-col items-start justify-center py-20">
          <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-sky-400">
            Available for opportunities
          </p>
          <h1 className="text-5xl font-extrabold leading-tight tracking-tight text-white sm:text-6xl">
            [Your Name]
          </h1>
          <p className="mt-3 text-xl font-medium text-slate-400">
            [Your Title — e.g. Software Developer / Data Engineer]
          </p>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-400">
            [Two-sentence bio. E.g. "I build data-driven web applications that turn complex datasets
            into clear, actionable visuals. Currently focused on supply chain intelligence and
            geospatial analytics."]
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <button
              onClick={() => scrollTo(projectsRef)}
              className="flex items-center gap-2 rounded-lg bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-sky-400"
            >
              View Projects <ChevronRight className="h-4 w-4" />
            </button>
            <a href={LINKS.resume} download
              className="flex items-center gap-2 rounded-lg border border-slate-600 px-5 py-2.5 text-sm font-semibold text-slate-300 transition-colors hover:border-slate-400 hover:text-white">
              <FileDown className="h-4 w-4" /> Download Resume
            </a>
          </div>
        </section>

        {/* ── Projects ──────────────────────────────────────────────────── */}
        <section ref={projectsRef} className="scroll-mt-20 pb-24">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-sky-400">Projects</p>
          <h2 className="mb-10 text-3xl font-extrabold text-white">What I&apos;ve built</h2>

          {/* FreightFlow — featured card */}
          <div className="rounded-2xl border border-slate-700/60 bg-slate-800/50 p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-sky-500/25 bg-sky-500/15">
                  <Truck className="h-5 w-5 text-sky-400" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">FreightFlow</h3>
                  <p className="text-xs text-slate-500">2025 · Solo project</p>
                </div>
              </div>
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400">
                Live
              </span>
            </div>

            <p className="mt-5 text-sm leading-relaxed text-slate-300">
              A US freight supply chain intelligence platform. Pick a finished product — automobiles,
              beef, pharmaceuticals, or steel — select an assembly hub, and visualise how precursor
              materials flow across America&apos;s freight network to reach it. Includes cost modelling,
              mode analysis, and concentration risk scoring based on 522k real freight records from
              the Bureau of Transportation Statistics.
            </p>

            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {FREIGHTFLOW_FEATURES.map(({ icon: Icon, label, desc }) => (
                <div key={label} className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-4">
                  <Icon className="mb-2 h-4 w-4 text-sky-400" />
                  <p className="text-xs font-semibold text-white">{label}</p>
                  <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{desc}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              {TECH_BADGES.map(t => <TechBadge key={t} label={t} />)}
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/freightflow"
                className="flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-sky-400">
                <Truck className="h-4 w-4" /> Live Demo
              </Link>
              <a href={LINKS.freightflow} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-300 transition-colors hover:border-slate-400 hover:text-white">
                <Github className="h-4 w-4" /> Source Code
              </a>
            </div>
          </div>

          {/* Placeholder for future projects */}
          <div className="mt-4 flex items-center justify-center rounded-2xl border border-dashed border-slate-700/60 p-10">
            <p className="text-sm text-slate-600">More projects coming soon</p>
          </div>
        </section>

        {/* ── About ─────────────────────────────────────────────────────── */}
        <section ref={aboutRef} className="scroll-mt-20 pb-24">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-sky-400">About</p>
          <h2 className="mb-8 text-3xl font-extrabold text-white">Background</h2>

          <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
            <div className="space-y-4 text-sm leading-relaxed text-slate-400">
              <p>
                [Paragraph 1 — where you&apos;re from, your background, what you studied or how you got
                into software / data. Keep it brief and personal.]
              </p>
              <p>
                [Paragraph 2 — what you&apos;re interested in technically. Supply chain, data engineering,
                full-stack development — whatever is most relevant to the roles you&apos;re targeting.]
              </p>
              <p>
                [Paragraph 3 — optional. Outside interests, what motivates you, what you&apos;re looking for next.]
              </p>

              <div className="flex flex-wrap gap-4 pt-2">
                <a href={LINKS.github} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-sky-400 transition-colors hover:text-sky-300">
                  <Github className="h-4 w-4" />
                  <span className="text-xs font-medium">GitHub</span>
                </a>
                <a href={LINKS.linkedin} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-sky-400 transition-colors hover:text-sky-300">
                  <Linkedin className="h-4 w-4" />
                  <span className="text-xs font-medium">LinkedIn</span>
                </a>
                <a href={LINKS.email}
                  className="flex items-center gap-1.5 text-sky-400 transition-colors hover:text-sky-300">
                  <Mail className="h-4 w-4" />
                  <span className="text-xs font-medium">[your@email.com]</span>
                </a>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {SKILLS.map(group => (
                <SkillGroup key={group.category} {...group} />
              ))}
            </div>
          </div>
        </section>

        {/* ── Resume ────────────────────────────────────────────────────── */}
        <section ref={resumeRef} className="scroll-mt-20 pb-24">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-sky-400">Resume</p>
          <h2 className="mb-8 text-3xl font-extrabold text-white">Experience &amp; Education</h2>

          <div className="rounded-2xl border border-slate-700/60 bg-slate-800/50 p-10 text-center">
            <FileDown className="mx-auto mb-4 h-10 w-10 text-slate-500" />
            <p className="text-sm text-slate-400">Download my full resume as a PDF</p>
            <a href={LINKS.resume} download
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-sky-500 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-sky-400">
              <FileDown className="h-4 w-4" /> Download Resume
            </a>
            <p className="mt-4 text-[11px] text-slate-600">PDF · Updated [Month Year]</p>
          </div>
        </section>

      </main>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-700/50 py-8">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6">
          <p className="text-xs text-slate-600">© {new Date().getFullYear()} [Your Name]</p>
          <div className="flex items-center gap-1 text-[11px] text-slate-700">
            <span>Built with Next.js · Deployed on Vercel</span>
            <ExternalLink className="ml-1 h-3 w-3" />
          </div>
        </div>
      </footer>
    </div>
  )
}
