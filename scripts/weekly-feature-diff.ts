#!/usr/bin/env npx ts-node
/**
 * Weekly Feature Inventory Diff Script
 *
 * Analyzes code changes from the past week and updates:
 * - docs/PROJECT_FEATURES.md (change log)
 * - docs/feature-evolution/*.md (memory)
 * - docs/weekly-reports/YYYY-WW.md (summary)
 *
 * Usage:
 *   npx ts-node scripts/weekly-feature-diff.ts
 *   npx ts-node scripts/weekly-feature-diff.ts --since="2026-02-01"
 *   npx ts-node scripts/weekly-feature-diff.ts --dry-run
 */

import { execSync } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'

// Parse CLI args
const args = process.argv.slice(2)
const dryRun = args.includes('--dry-run')
const sinceArg = args.find((a) => a.startsWith('--since='))?.split('=')[1] || '7 days ago'
const untilArg = args.find((a) => a.startsWith('--until='))?.split('=')[1] || 'now'

const DOCS_DIR = path.join(__dirname, '..', 'docs')
const FEATURES_FILE = path.join(DOCS_DIR, 'PROJECT_FEATURES.md')
const EVOLUTION_DIR = path.join(DOCS_DIR, 'feature-evolution')
const REPORTS_DIR = path.join(DOCS_DIR, 'weekly-reports')

// Ensure directories exist
;[EVOLUTION_DIR, REPORTS_DIR].forEach((dir) => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
})

interface GitCommit {
  hash: string
  message: string
  files: string[]
  date: string
}

interface FileCategory {
  components: string[]
  endpoints: string[]
  types: string[]
  migrations: string[]
  tests: string[]
  other: string[]
}

function getCommits(): GitCommit[] {
  const log = execSync(
    `git log --since="${sinceArg}" --until="${untilArg}" --name-only --pretty=format:"COMMIT:%H|%s|%ai" 2>/dev/null || echo ""`,
    { encoding: 'utf-8' }
  )

  if (!log.trim()) return []

  const commits: GitCommit[] = []
  let current: GitCommit | null = null

  for (const line of log.split('\n')) {
    if (line.startsWith('COMMIT:')) {
      if (current) commits.push(current)
      const [hash, message, date] = line.slice(7).split('|')
      current = { hash, message, date, files: [] }
    } else if (line.trim() && current) {
      current.files.push(line.trim())
    }
  }
  if (current) commits.push(current)

  return commits
}

function categorizeFiles(commits: GitCommit[]): FileCategory {
  const all = new Set<string>()
  commits.forEach((c) => c.files.forEach((f) => all.add(f)))

  const files = Array.from(all)
  return {
    components: files.filter((f) => f.includes('/components/') && f.endsWith('.tsx')),
    endpoints: files.filter((f) => f.startsWith('app/api/') && f.endsWith('.py')),
    types: files.filter((f) => f.includes('/types/') && f.endsWith('.ts')),
    migrations: files.filter((f) => f.startsWith('migrations/') && f.endsWith('.sql')),
    tests: files.filter((f) => f.includes('test') && (f.endsWith('.py') || f.endsWith('.ts'))),
    other: files.filter(
      (f) =>
        !f.includes('/components/') &&
        !f.startsWith('app/api/') &&
        !f.includes('/types/') &&
        !f.startsWith('migrations/') &&
        !f.includes('test')
    ),
  }
}

function getWeekNumber(): string {
  const now = new Date()
  const start = new Date(now.getFullYear(), 0, 1)
  const diff = now.getTime() - start.getTime()
  const oneWeek = 604800000
  const week = Math.ceil(diff / oneWeek)
  return `${now.getFullYear()}-W${week.toString().padStart(2, '0')}`
}

function generateReport(commits: GitCommit[], categories: FileCategory): string {
  const week = getWeekNumber()
  const totalFiles =
    categories.components.length +
    categories.endpoints.length +
    categories.types.length +
    categories.migrations.length

  let report = `# Week ${week.split('-W')[1]}, ${week.split('-W')[0]}

> Auto-generated on ${new Date().toISOString().split('T')[0]}
> Commits analyzed: ${commits.length}

## Summary

- **${commits.length}** commits
- **${totalFiles}** files changed
- **${categories.components.length}** frontend components
- **${categories.endpoints.length}** backend endpoints
- **${categories.migrations.length}** migrations

## Commits

| Hash | Message |
|------|---------|
${commits.map((c) => `| \`${c.hash.slice(0, 7)}\` | ${c.message} |`).join('\n')}

## Changed Files by Category

### Frontend Components (${categories.components.length})
${categories.components.length ? categories.components.map((f) => `- \`${f}\``).join('\n') : '_None_'}

### Backend Endpoints (${categories.endpoints.length})
${categories.endpoints.length ? categories.endpoints.map((f) => `- \`${f}\``).join('\n') : '_None_'}

### Types (${categories.types.length})
${categories.types.length ? categories.types.map((f) => `- \`${f}\``).join('\n') : '_None_'}

### Migrations (${categories.migrations.length})
${categories.migrations.length ? categories.migrations.map((f) => `- \`${f}\``).join('\n') : '_None_'}

## Feature Impact Analysis

> TODO: Claude analysis would go here
> For now, manually review commits to identify:
> - New features (need IDs)
> - Modified features
> - Assumptions validated/challenged

## Questions for Next Week

- [ ] Review feedback from beta testers
- [ ] Validate assumptions for new features
- [ ] Update feature evolution docs

---
*Generated by \`scripts/weekly-feature-diff.ts\`*
`

  return report
}

function updateChangeLog(commits: GitCommit[]): void {
  if (!fs.existsSync(FEATURES_FILE)) {
    console.log('PROJECT_FEATURES.md not found, skipping change log update')
    return
  }

  const content = fs.readFileSync(FEATURES_FILE, 'utf-8')
  const date = new Date().toISOString().split('T')[0]

  // Find the Change Log section
  const changeLogMarker = '## Change Log'
  const idx = content.indexOf(changeLogMarker)
  if (idx === -1) {
    console.log('Change Log section not found in PROJECT_FEATURES.md')
    return
  }

  // Build new entry
  const summaries = commits.slice(0, 5).map((c) => c.message).join('; ')
  const entry = `| ${date} | Weekly update | - | ${summaries.slice(0, 80)}... |`

  // Insert after table header
  const tableStart = content.indexOf('|---', idx)
  if (tableStart === -1) return

  const tableEnd = content.indexOf('\n\n', tableStart)
  const beforeTable = content.slice(0, tableStart)
  const tableHeader = content.slice(tableStart, content.indexOf('\n', tableStart) + 1)
  const existingRows = content.slice(content.indexOf('\n', tableStart) + 1, tableEnd)
  const afterTable = content.slice(tableEnd)

  const newContent = beforeTable + tableHeader + entry + '\n' + existingRows + afterTable

  if (!dryRun) {
    fs.writeFileSync(FEATURES_FILE, newContent)
    console.log('Updated PROJECT_FEATURES.md change log')
  } else {
    console.log('[DRY RUN] Would update PROJECT_FEATURES.md')
  }
}

async function main() {
  console.log(`\n🔍 Analyzing commits since "${sinceArg}" until "${untilArg}"...\n`)

  const commits = getCommits()
  if (commits.length === 0) {
    console.log('No commits found in date range.')
    return
  }

  console.log(`Found ${commits.length} commits:\n`)
  commits.forEach((c) => console.log(`  ${c.hash.slice(0, 7)} ${c.message}`))

  const categories = categorizeFiles(commits)
  console.log(`\n📁 File categories:`)
  console.log(`  Components: ${categories.components.length}`)
  console.log(`  Endpoints: ${categories.endpoints.length}`)
  console.log(`  Types: ${categories.types.length}`)
  console.log(`  Migrations: ${categories.migrations.length}`)

  // Generate weekly report
  const report = generateReport(commits, categories)
  const week = getWeekNumber()
  const reportPath = path.join(REPORTS_DIR, `${week}.md`)

  if (!dryRun) {
    fs.writeFileSync(reportPath, report)
    console.log(`\n📝 Created weekly report: ${reportPath}`)
  } else {
    console.log(`\n[DRY RUN] Would create: ${reportPath}`)
  }

  // Update change log
  updateChangeLog(commits)

  if (!dryRun) {
    console.log(`\n✅ Done! Review the weekly report and update feature evolution docs manually.`)
    console.log(`\nNext steps:`)
    console.log(`  1. Review ${reportPath}`)
    console.log(`  2. Identify new features and assign IDs`)
    console.log(`  3. Update docs/feature-evolution/*.md with learnings`)
    console.log(`  4. Commit changes: git add docs/ && git commit -m "chore: weekly feature update"`)
  }
}

main().catch(console.error)
