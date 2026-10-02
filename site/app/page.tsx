"use client";

import { useEffect, useMemo, useState } from "react";
import rawBundle from "./drugs.json";
import parameterAudit from "../../docs/research/2026-10-02-all-drug-audit/all-drug-audit.json";

type Language = "ja" | "en";
const auditLabels: Record<string, [string, string]> = {
  VERIFIED_VALUE_ONLY: ["数値照合", "Value matched"],
  QUALIFIED: ["条件付き", "Qualified"],
  CONTRADICTION: ["不整合", "Contradiction"],
  FIXTURE_ASSUMPTION: ["仮定", "Fixture assumption"],
  UNVERIFIED: ["未確認", "Unverified"],
  DERIVED: ["導出", "Derived"],
};
const auditReportUrl = "https://github.com/Y-Fukiya/pkdummy-harness/blob/main/docs/research/2026-10-02-all-drug-audit/REPORT.md";
function AuditPanel({ slug, lang }: { slug?: string; lang: Language }) {
  const item = parameterAudit.drugs.find((drug) => drug.slug === slug);
  return <section className="panel audit-panel" aria-label={lang === "ja" ? "最新パラメータ監査" : "Latest parameter audit"}>
    <span className="eyebrow">PARAMETER AUDIT · {parameterAudit.audit_date}</span>
    <h2>{lang === "ja" ? "最新パラメータ監査" : "Latest parameter audit"}</h2>
    <p>{lang === "ja" ? "37薬剤・148項目を監査。数値照合はモデル採用の承認ではありません。全37薬剤の臨床モデル採用は保留です。" : "37 drugs and 148 parameters reviewed. Matching a value does not qualify a model. Clinical model use remains on hold for all 37 drugs."}</p>
    <p className="audit-scope">{lang === "ja" ? "監査対象は記録されたローカル作業版の入力snapshotです。掲載先mainの全薬剤YAMLを監査済みという意味ではありません。従来のPKチェック・確認状態と今回の監査判定は別に表示します。" : "The audit covers the recorded local working-tree snapshot, not every canonical YAML in main. Earlier PK checks and the new audit verdicts are separate assessments."}</p>
    {item ? <>
      <p>{item.summary}</p>
      <div className="audit-items">{item.parameters.map((entry) => <details key={entry.parameter}>
        <summary><strong>{({clearance: "CL", volume: "V", half_life: "t½", bioavailability: "F"} as Record<string, string>)[entry.parameter] ?? entry.parameter}</strong><span className={`audit-verdict audit-${entry.verdict.toLowerCase()}`}>{auditLabels[entry.verdict]?.[lang === "ja" ? 0 : 1] ?? entry.verdict}</span></summary>
        <p>{entry.reason}</p><p><strong>{lang === "ja" ? "次の対応: " : "Required action: "}</strong>{entry.required_action}</p>
        <p>{entry.locator} · {entry.access_level}</p>
        {entry.source_urls.map((url) => <a key={url} href={url} target="_blank" rel="noreferrer">{url}</a>)}
      </details>)}</div>
    </> : <div className="audit-counts">{Object.entries(parameterAudit.verdict_counts).map(([key, count]) => <span key={key}>{auditLabels[key]?.[lang === "ja" ? 0 : 1] ?? key}<strong>{count}</strong></span>)}</div>}
    <a href={auditReportUrl}>{lang === "ja" ? "監査レポート全文" : "Full audit report"} ↗</a>
  </section>;
}

type JsonObject = Record<string, unknown>;

type Source = {
  id: string | null;
  display_id: string;
  url: string | null;
  index: number;
  kind?: string;
  identifier?: string | null;
  bibliography?: {
    title?: string | null;
    journal?: string | null;
    pubdate?: string | null;
    authors?: string[];
    doi?: string | null;
    pubmed_url?: string | null;
  };
};

type EvidenceClaim = {
  claim_id: string;
  claim_type: string;
  parameter: string;
  source_field: string;
  source_id: string | null;
  raw_value: unknown;
  normalized_value: unknown;
  normalized_unit: string | null;
  evidence_status: string;
  evidence_level: string;
  evidence_summary: string | null;
  exact_quote: string | null;
  source_locator: string | null;
  missing: string[];
};

type PharmacologyClaim = {
  claim_id: string;
  claim_type: string;
  statement: unknown;
  source_id: string | null;
  source_key?: string | null;
  source: Source | null;
  claim_status: string;
  source_fit_status: string;
  jurisdiction: string;
  population_context: string;
  route_or_formulation: string;
  study_context: string;
  evidence_status: string;
  evidence_level: string;
  evidence_summary: unknown;
  exact_quote: string | null;
  source_locator: string | null;
  missing: string[];
};

type Drug = {
  slug: string;
  id: string | null;
  name: string;
  route: string | null;
  sources: Source[];
  raw: JsonObject;
  parsed: JsonObject;
  derived: JsonObject;
  provenance: JsonObject;
  targets: JsonObject;
  spec: JsonObject;
  review: {
    provenance_field_count: number;
    needs_review_count: number;
    evidence_claim_count: number;
    evidence_unresolved_count: number;
    evidence_citation_gap_count: number;
    strict_status?: string | null;
    open_review_count?: number;
    known_limitation_count?: number;
    structural_mismatch_acknowledged: boolean;
  };
  pharmacology: {
    status: string;
    review_stage?: string;
    claim_count: number;
    source_candidate_count?: number;
    reviewed_count?: number;
    exact_quote_count?: number;
    source_locator_count?: number;
    claims: PharmacologyClaim[];
  };
  evidence: {
    schema_version: string;
    summary: {
      claim_count: number;
      checked_summary_count: number;
      fixture_check_count: number;
      unresolved_count: number;
      value_verified_count: number;
      exact_quote_count: number;
      source_locator_count: number;
      citation_gap_count: number;
    };
    claims: EvidenceClaim[];
  };
};

type DrugBundle = {
  schema_version: string;
  source: string;
  drug_count: number;
  drugs: Drug[];
};

const initialBundle = rawBundle as unknown as DrugBundle;

const copy = {
  ja: {
    brand: "PK decision atlas",
    kicker: "PK PARAMETER LIBRARY",
    title: "薬物動態パラメータの根拠台帳",
    intro:
      "原文、単位変換、導出値、モデル採用値をひとつの流れで確認できる、英日対応の科学ドキュメントです。",
    catalog: "薬剤カタログ",
    catalogIntro: "現在のcanonical YAMLから生成された37薬剤のレビュー入口",
    search: "薬剤名、slug、原文、URLを検索",
    allRoutes: "すべての経路",
    oral: "経口",
    sublingual: "舌下",
    iv: "静注",
    sourceCount: "出典",
    drugs: "薬剤",
    review: "レビュー状態",
    needsReview: "PK要確認",
    citationGap: "PK補足注記",
    mobileCatalogJump: "薬剤を検索する",
    readGuide: "読み方",
    aboutTitle: "このサイトの読み方",
    aboutIntro: "値の意味を混ぜずに、原文からモデル採用値まで順に確認できます。",
    aboutSourceTitle: "原文・出典",
    aboutSourceText: "まず、原文と出典リンクがどの薬剤・製剤に対応するかを確認します。",
    aboutDerivedTitle: "正規化・導出",
    aboutDerivedText: "次に、単位変換、70 kg換算、CL/V basisなどの導出過程を確認します。",
    aboutModelTitle: "モデル採用値",
    aboutModelText: "最後に、fixtureのspecが採用するthetaと、文献のcheck-only値を分けて読みます。",
    reviewed: "PKデータ確認済み",
    pharmacologyMetric: "薬理レビュー",
    pharmacologyMetricNote: "候補とレビュー済み件数を分けて表示",
    pharmacologyCardReviewed: "薬理: 確認済み",
    pharmacologyCardCandidate: "薬理: 原典候補",
    notRecorded: "provenance未登録",
    route: "投与経路",
    basis: "CL/V basis",
    referenceWeight: "基準体重",
    sources: "出典リンク",
    evidenceChain: "値の証拠チェーン",
    raw: "原文 / raw",
    parsed: "パース済み / parsed",
    derived: "導出値 / derived",
    model: "モデル採用値 / model",
    rawHint: "レンジ・単位を含む元記載。内容は補正せず保存しています。",
    parsedHint: "シミュレーションに使える数値と単位へ正規化した値です。",
    derivedHint: "70 kg換算、CL/V、systemic・apparent basisを含む導出値です。",
    modelHint: "spec_pk1_* が実際に採用するtheta。文献値とは別に確認します。",
    parameterTable: "主要パラメータ",
    parameter: "パラメータ",
    value: "値",
    sourceField: "source field",
    status: "状態",
    calculation: "計算・解釈",
    sourceRegister: "出典レジスター",
    evidenceAudit: "値単位の証拠監査",
    evidenceAuditIntro: "URLの存在、確認済み要約、引用箇所付きの値単位証拠を分けて表示します。",
    evidenceClaim: "claim",
    evidence: "証拠レベル",
    missingEvidence: "不足項目",
    exactQuote: "引用",
    sourceLocator: "引用箇所",
    noExactQuote: "逐語引用未登録",
    noSourceLocator: "節・表・ページ未登録",
    checkedSummary: "要約確認済み",
    fixtureCheck: "fixture整合性チェック",
    citationGaps: "引用補足",
    unresolvedEvidence: "証拠未解決",
    sourceMappingNeeded: "source mapping要",
    valueVerified: "値単位で確認済み",
    bibliography: "書誌メタデータ",
    targetChecks: "ターゲットと検証",
    pharmacology: "薬効・作用機序",
    pharmacologyPending:
      "薬効・作用機序の原典候補を登録しています。現段階では逐語引用と節・表・ページが未確認のため、確認済みの薬理学的証拠とは扱いません。",
    pharmacologyPartial: "原典候補（確認待ち）",
    pharmacologyCurated: "薬理学レビュー済み",
    pharmacologyClaim: "主張",
    pharmacologySourceCandidate: "source candidate",
    pharmacologyClaimStatus: "主張状態",
    pharmacologySourceFit: "原典適合性",
    pharmacologyReviewedContext: "引用・適合性・文脈確認済み",
    pharmacologyMissing: "確認待ち",
    pharmacologyNoClaims: "薬効claimは未登録です。",
    notClinical:
      "これは臨床判断や用量決定の文書ではなく、再現可能なworkflow fixtureの根拠台帳です。",
    back: "薬剤一覧へ戻る",
    openSource: "出典を開く",
    noResults: "条件に一致する薬剤はありません。",
    noSource: "URL未登録",
    language: "言語",
    english: "English",
    japanese: "日本語",
    mismatch: "1-compartment不一致",
    acknowledged: "fixture limitationとして確認済み",
    checkOnly: "検証専用",
    simulation: "シミュレーション採用",
    fixturePolicy: "fixture仮定",
    sourceMapping: "source mapping",
    unknown: "未確認",
    tableScrollHint: "表は横にスクロールできます。",
  },
  en: {
    brand: "PK decision atlas",
    kicker: "PK PARAMETER LIBRARY",
    title: "PK parameter evidence atlas",
    intro:
      "A bilingual scientific guide from source text and unit conversion to derived values and model parameters.",
    catalog: "Drug catalog",
    catalogIntro: "A review entry point for 37 drugs generated from the current canonical YAML.",
    search: "Search drug name, slug, raw text, or URL",
    allRoutes: "All routes",
    oral: "Oral",
    sublingual: "Sublingual",
    iv: "IV",
    sourceCount: "sources",
    drugs: "drugs",
    review: "Review status",
    needsReview: "PK needs review",
    citationGap: "PK context notes",
    mobileCatalogJump: "Search the drug catalog",
    readGuide: "How to read",
    aboutTitle: "How to read this site",
    aboutIntro: "Follow the evidence chain in order without mixing raw, derived, and model values.",
    aboutSourceTitle: "Raw source",
    aboutSourceText: "First confirm which drug, formulation, and source the original statement belongs to.",
    aboutDerivedTitle: "Normalized and derived",
    aboutDerivedText: "Then check unit conversion, 70 kg scaling, and the CL/V basis used by the fixture.",
    aboutModelTitle: "Model value",
    aboutModelText: "Finally separate the theta used by the spec from literature values kept as check-only targets.",
    reviewed: "PK data checked",
    pharmacologyMetric: "Pharmacology review",
    pharmacologyMetricNote: "Candidates and reviewed claims are counted separately",
    pharmacologyCardReviewed: "Pharm: reviewed",
    pharmacologyCardCandidate: "Pharm: candidate",
    notRecorded: "Provenance not recorded",
    route: "Route",
    basis: "CL/V basis",
    referenceWeight: "Reference weight",
    sources: "Source links",
    evidenceChain: "Evidence chain",
    raw: "Raw statement",
    parsed: "Parsed value",
    derived: "Derived value",
    model: "Model value",
    rawHint: "The original statement, including ranges and units, is preserved.",
    parsedHint: "Normalized values and units used by the fixture workflow.",
    derivedHint: "Derived values including 70 kg scaling and apparent/systemic basis.",
    modelHint: "The theta actually used by spec_pk1_*.yml, reviewed separately from literature values.",
    parameterTable: "Key parameters",
    parameter: "Parameter",
    value: "Value",
    sourceField: "Source field",
    status: "Status",
    calculation: "Calculation / interpretation",
    sourceRegister: "Source register",
    evidenceAudit: "Value-level evidence audit",
    evidenceAuditIntro: "URL presence, checked summaries, and value-level citations are shown as separate states.",
    evidenceClaim: "Claim",
    evidence: "Evidence level",
    missingEvidence: "Missing",
    exactQuote: "Quote",
    sourceLocator: "Locator",
    noExactQuote: "No verbatim quote registered",
    noSourceLocator: "No section/table/page locator",
    checkedSummary: "Checked summary",
    fixtureCheck: "Fixture consistency check",
    citationGaps: "Citation notes",
    unresolvedEvidence: "Evidence unresolved",
    sourceMappingNeeded: "Source mapping needed",
    valueVerified: "Value verified",
    bibliography: "Bibliographic metadata",
    targetChecks: "Targets and checks",
    pharmacology: "Pharmacology and mechanism",
    pharmacologyPending:
      "Source candidates for pharmacology and mechanism are registered. Verbatim excerpts and precise section/table/page locators are still pending, so these are not presented as reviewed pharmacology evidence.",
    pharmacologyPartial: "Source candidate (review pending)",
    pharmacologyCurated: "Pharmacology reviewed",
    pharmacologyClaim: "Claim",
    pharmacologySourceCandidate: "source candidate",
    pharmacologyClaimStatus: "Claim status",
    pharmacologySourceFit: "Source fit",
    pharmacologyReviewedContext: "Quote, fit, and context reviewed",
    pharmacologyMissing: "Review pending",
    pharmacologyNoClaims: "No pharmacology claim is registered.",
    notClinical:
      "This is a reproducible workflow-fixture evidence record, not a clinical or dose-selection document.",
    back: "Back to drug catalog",
    openSource: "Open source",
    noResults: "No drugs match the current filters.",
    noSource: "No URL recorded",
    language: "Language",
    english: "English",
    japanese: "日本語",
    mismatch: "1-compartment mismatch",
    acknowledged: "Acknowledged as a fixture limitation",
    checkOnly: "Check only",
    simulation: "Simulation parameter",
    fixturePolicy: "Fixture policy",
    sourceMapping: "Source mapping",
    unknown: "Unconfirmed",
    tableScrollHint: "Scroll horizontally to view the full table.",
  },
} as const;

function record(value: unknown): JsonObject {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : {};
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatValue(value: unknown, lang: Language): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    if (Math.abs(value) > 0 && Math.abs(value) < 0.001) return value.toExponential(3);
    return value.toLocaleString(lang === "ja" ? "ja-JP" : "en-US", {
      maximumFractionDigits: 4,
    });
  }
  if (Array.isArray(value)) return value.map((item) => formatValue(item, lang)).join(" – ");
  if (typeof value === "object") {
    return Object.entries(value as JsonObject)
      .map(([key, item]) => `${key}: ${formatValue(item, lang)}`)
      .join(" · ");
  }
  return String(value);
}

function shortText(value: unknown, lang: Language, limit = 180): string {
  const text = formatValue(value, lang);
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function localizedText(value: unknown, lang: Language, limit = 180): string {
  const object = record(value);
  if (typeof object[lang] === "string") return shortText(object[lang], lang, limit);
  return shortText(value, lang, limit);
}

function routeLabel(route: unknown, lang: Language): string {
  const value = String(route ?? "").toLowerCase();
  if (value.includes("iv") || value.includes("intraven")) return copy[lang].iv;
  if (value.includes("sl") || value.includes("subling")) return copy[lang].sublingual;
  if (value.includes("po") || value.includes("oral")) return copy[lang].oral;
  return value || copy[lang].unknown;
}

function routeCode(route: unknown): string {
  const value = String(route ?? "").toLowerCase();
  if (value.includes("iv") || value.includes("intraven")) return "iv";
  if (value.includes("sl") || value.includes("subling")) return "sl";
  if (value.includes("po") || value.includes("oral")) return "po";
  return value;
}

function hasUnresolvedEvidence(drug: Drug): boolean {
  return (drug.evidence?.summary?.unresolved_count ?? 0) > 0;
}

function hasOpenReview(drug: Drug): boolean {
  return (drug.review?.open_review_count ?? 0) > 0 || drug.review.needs_review_count > 0 || hasUnresolvedEvidence(drug);
}

function hasCitationGap(drug: Drug): boolean {
  return (drug.evidence?.summary?.citation_gap_count ?? 0) > 0;
}

function statusForDrug(drug: Drug, lang: Language): string {
  const audit = parameterAudit.drugs.find((entry) => entry.slug === drug.slug);
  if (audit) {
    const order = ["CONTRADICTION", "UNVERIFIED", "QUALIFIED", "FIXTURE_ASSUMPTION", "DERIVED", "VERIFIED_VALUE_ONLY"];
    const verdict = order.find((key) => audit.parameters.some((entry) => entry.verdict === key))!;
    return `${lang === "ja" ? "監査" : "Audit"}: ${auditLabels[verdict][lang === "ja" ? 0 : 1]}`;
  }
  if (drug.review.provenance_field_count === 0) return copy[lang].notRecorded;
  if (hasOpenReview(drug)) return copy[lang].needsReview;
  if (hasCitationGap(drug)) return copy[lang].citationGap;
  return copy[lang].reviewed;
}

function statusClass(drug: Drug): string {
  const audit = parameterAudit.drugs.find((entry) => entry.slug === drug.slug);
  if (audit) return audit.parameters.some((entry) => ["CONTRADICTION", "UNVERIFIED"].includes(entry.verdict)) ? "status warning" : "status context";
  if (drug.review.provenance_field_count === 0) return "status muted";
  if (hasOpenReview(drug)) return "status warning";
  if (hasCitationGap(drug)) return "status context";
  return "status good";
}

function pharmacologyStatusForDrug(drug: Drug, lang: Language): string {
  return drug.pharmacology?.status === "curated"
    ? copy[lang].pharmacologyCardReviewed
    : copy[lang].pharmacologyCardCandidate;
}

function pharmacologyStatusClass(drug: Drug): string {
  return drug.pharmacology?.status === "curated" ? "reviewed" : "candidate";
}

function evidenceStatusLabel(claim: EvidenceClaim, lang: Language): string {
  if (claim.evidence_level === "value_verified") return copy[lang].valueVerified;
  if (claim.evidence_level === "fixture_check") return copy[lang].fixtureCheck;
  if (claim.evidence_status === "checked_summary") return copy[lang].checkedSummary;
  if (claim.evidence_status === "needs_source_mapping") return copy[lang].sourceMappingNeeded;
  return copy[lang].unresolvedEvidence;
}

function evidenceStatusClass(claim: EvidenceClaim): string {
  if (claim.evidence_level === "value_verified") return "mini-status good";
  if (claim.evidence_level === "summary_only") return "mini-status context";
  if (claim.evidence_status === "checked_summary") return "mini-status warning";
  return "mini-status warning";
}

function parameterRows(drug: Drug, lang: Language) {
  const parsed = record(drug.parsed);
  const derived = record(drug.derived);
  const provenance = record(drug.provenance);
  const clearance = record(parsed.clearance);
  const volume = record(parsed.volume);
  const basis = String(parsed.clearance_basis ?? "apparent").toLowerCase();
  const entries = [
    {
      key: "CL",
      value: `${formatValue(derived.CL_abs_L_per_h_at_70kg, lang)} L/h`,
      source: "derived.CL_abs_L_per_h_at_70kg",
      note: "CL/V independent fixture parameter",
      prov: provenance.CL_abs_L_per_h_at_70kg,
      fixturePolicy: false,
    },
    {
      key: "V",
      value: `${formatValue(derived.V_abs_L_at_70kg, lang)} L`,
      source: "derived.V_abs_L_at_70kg",
      note: "70 kg normalized volume",
      prov: provenance.V_abs_L_at_70kg,
      fixturePolicy: false,
    },
    {
      key: "t½",
      value: `${formatValue(parsed.half_life_h, lang)} h`,
      source: "pk_parsed.half_life_h",
      note: "check-only literature target",
      prov: provenance.t_half_h,
      fixturePolicy: false,
    },
    {
      key: "F",
      value: formatValue(parsed.bioavailability_frac, lang),
      source: "pk_parsed.bioavailability_frac",
      note: "fraction; interpretation depends on CL/V basis",
      prov: provenance.bioavailability_frac,
      fixturePolicy: basis !== "systemic" && !provenance.bioavailability_frac,
    },
    {
      key: "raw CL",
      value: `${formatValue(clearance.value, lang)} ${formatValue(clearance.unit, lang)}`,
      source: "pk_parsed.clearance",
      note: "parsed input",
      prov: provenance.CL_abs_L_per_h_at_70kg,
      fixturePolicy: false,
    },
    {
      key: "raw V",
      value: `${formatValue(volume.value, lang)} ${formatValue(volume.unit, lang)}`,
      source: "pk_parsed.volume",
      note: "parsed input",
      prov: provenance.V_abs_L_at_70kg,
      fixturePolicy: false,
    },
  ];
  return entries.map((entry) => {
    const provenanceEntry = record(entry.prov);
    const sourceStatus = provenanceEntry.source_review_status;
    return {
      ...entry,
      status:
        entry.fixturePolicy
          ? lang === "ja"
            ? "fixture仮定"
            : "Fixture policy"
          : sourceStatus === "checked"
          ? lang === "ja"
            ? "確認済み"
            : "Checked"
          : sourceStatus || (lang === "ja" ? "未確認" : "Unconfirmed"),
    };
  });
}

function metricNumber(value: unknown): string {
  const number = numberValue(value);
  if (number === null) return "—";
  if (Math.abs(number) < 0.001) return number.toExponential(2);
  return number.toFixed(number >= 100 ? 0 : 2);
}

function SourceList({ drug, lang }: { drug: Drug; lang: Language }) {
  const t = copy[lang];
  return (
    <section className="panel source-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">SOURCE REGISTER</span>
          <h2>{t.sourceRegister}</h2>
        </div>
        <span className="count-pill">{drug.sources.length}</span>
      </div>
      {drug.sources.length ? (
        <ol className="source-list">
          {drug.sources.map((source) => (
            <li key={`${source.display_id}-${source.index}`}>
              <span className="source-id">{source.display_id}</span>
              <div>
                {source.url ? (
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.url.replace(/^https?:\/\//, "")}
                    <span aria-hidden="true"> ↗</span>
                  </a>
                ) : (
                  <span className="muted-text">{t.noSource}</span>
                )}
                {source.kind && <span className="source-kind">{source.kind}{source.identifier ? ` · ${source.identifier}` : ""}</span>}
                {source.bibliography?.title && (
                  <span className="source-bibliography">
                    {source.bibliography.title}
                    {source.bibliography.journal ? ` · ${source.bibliography.journal}` : ""}
                    {source.bibliography.pubdate ? ` · ${source.bibliography.pubdate}` : ""}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="muted-text">{t.noSource}</p>
      )}
    </section>
  );
}

function EvidenceAudit({ drug, lang }: { drug: Drug; lang: Language }) {
  const t = copy[lang];
  const claims = drug.evidence?.claims ?? [];
  const sourceById = new Map(drug.sources.map((source) => [source.id, source]));
  const summary = drug.evidence?.summary;
  return (
    <section className="panel evidence-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">EVIDENCE REGISTER</span>
          <h2>{t.evidenceAudit}</h2>
          <p className="section-subtitle">{t.evidenceAuditIntro}</p>
        </div>
        <span className="count-pill">{summary?.claim_count ?? claims.length}</span>
      </div>
      <div className="evidence-summary">
        <div><strong>{summary?.value_verified_count ?? 0}</strong><span>{t.valueVerified}</span></div>
        <div><strong>{summary?.checked_summary_count ?? 0}</strong><span>{t.checkedSummary}</span></div>
        <div><strong>{summary?.fixture_check_count ?? 0}</strong><span>{t.fixtureCheck}</span></div>
        <div><strong>{summary?.citation_gap_count ?? claims.length}</strong><span>{t.citationGaps}</span></div>
        <div><strong>{summary?.unresolved_count ?? claims.length}</strong><span>{t.unresolvedEvidence}</span></div>
      </div>
      {claims.length ? (
        <>
        <p className="table-scroll-hint">{t.tableScrollHint}</p>
        <div className="table-wrap">
          <table className="evidence-table">
            <thead>
              <tr><th>{t.evidenceClaim}</th><th>{t.sourceRegister}</th><th>{t.evidence}</th><th>{t.exactQuote} / {t.sourceLocator}</th><th>{t.missingEvidence}</th></tr>
            </thead>
            <tbody>
              {claims.map((claim) => {
                const source = claim.source_id ? sourceById.get(claim.source_id) : undefined;
                return (
                  <tr key={claim.claim_id}>
                    <th><strong>{claim.parameter}</strong><code>{claim.source_field}</code></th>
                    <td>{source?.display_id ?? (
                      claim.evidence_level === "fixture_check"
                        ? <span className="mini-status context">{t.fixturePolicy}</span>
                        : <span className="mini-status warning">{t.sourceMappingNeeded}</span>
                    )}</td>
                    <td><span className={evidenceStatusClass(claim)}>{evidenceStatusLabel(claim, lang)}</span>{claim.evidence_summary && <p className="evidence-summary-text">{shortText(claim.evidence_summary, lang, 190)}</p>}</td>
                    <td>
                      <span className={claim.exact_quote ? "evidence-present" : "evidence-missing"}>{claim.exact_quote ?? t.noExactQuote}</span>
                      <span className={claim.source_locator ? "evidence-present" : "evidence-missing"}>{claim.source_locator ?? t.noSourceLocator}</span>
                    </td>
                    <td>{claim.missing.length ? claim.missing.join(", ") : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        </>
      ) : <p className="muted-text">{t.unresolvedEvidence}</p>}
    </section>
  );
}

function DetailView({ drug, lang, onBack }: { drug: Drug; lang: Language; onBack: () => void }) {
  const t = copy[lang];
  const parsed = record(drug.parsed);
  const derived = record(drug.derived);
  const spec = record(drug.spec);
  const model = record(spec.model);
  const theta = record(model.theta);
  const targets = record(drug.targets);
  const halfLife = record(targets.t_half);
  const mismatch = record(halfLife.structural_mismatch);
  const cl = numberValue(derived.CL_abs_L_per_h_at_70kg);
  const volume = numberValue(derived.V_abs_L_at_70kg);
  const modelHalfLife = cl && volume ? Math.log(2) * volume / cl : null;
  const reportedHalfLife = numberValue(parsed.half_life_h);
  const mismatchPercent = modelHalfLife && reportedHalfLife
    ? Math.abs(modelHalfLife - reportedHalfLife) / reportedHalfLife * 100
    : null;
  const rows = parameterRows(drug, lang);

  return (
    <article className="detail-view">
      <button className="back-button" onClick={onBack} type="button">
        <span aria-hidden="true">←</span> {t.back}
      </button>
      <div className="detail-head">
        <div>
          <div className="eyebrow">{String(drug.id ?? drug.slug).toUpperCase()}</div>
          <h1>{drug.name}</h1>
          <p className="lead">
            {lang === "ja"
              ? "この薬剤の値が、どの原文からどのように変換され、どのfixtureパラメータに採用されたかを確認します。"
              : "Trace how source statements became normalized values, derived quantities, and fixture parameters."}
          </p>
        </div>
        <div className="detail-badges">
          <span className="route-badge">{routeLabel(drug.route, lang)}</span>
          <span className={statusClass(drug)}>{statusForDrug(drug, lang)}</span>
        </div>
      </div>

      <AuditPanel slug={drug.slug} lang={lang} />

      <div className="metrics detail-metrics">
        <div className="metric-card accent-blue">
          <span>CL</span>
          <strong>{metricNumber(derived.CL_abs_L_per_h_at_70kg)}</strong>
          <small>L/h · 70 kg</small>
        </div>
        <div className="metric-card accent-teal">
          <span>V</span>
          <strong>{metricNumber(derived.V_abs_L_at_70kg)}</strong>
          <small>L · 70 kg</small>
        </div>
        <div className="metric-card accent-gold">
          <span>t½ source</span>
          <strong>{metricNumber(parsed.half_life_h)}</strong>
          <small>h · {t.checkOnly}</small>
        </div>
        <div className="metric-card accent-purple">
          <span>CL/V basis</span>
          <strong className="metric-word">{formatValue(parsed.clearance_basis, lang)}</strong>
          <small>{t.referenceWeight}: {formatValue(parsed.weight_ref_kg_for_abs, lang)} kg</small>
        </div>
      </div>

      <section className="panel decision-panel" id="about">
        <div className="section-heading">
          <div>
            <span className="eyebrow">INTERPRETATION SUMMARY</span>
            <h2>{lang === "ja" ? "この値をどう読むか" : "How to read this evidence"}</h2>
          </div>
          <span className="decision-mark">{hasOpenReview(drug) ? "REVIEW" : "TRACEABLE"}</span>
        </div>
        <p>
          {lang === "ja"
            ? `このfixtureでは CL=${metricNumber(derived.CL_abs_L_per_h_at_70kg)} L/h と V=${metricNumber(derived.V_abs_L_at_70kg)} L を独立した1-compartmentパラメータとして扱います。文献t½ ${metricNumber(parsed.half_life_h)} hは下流のcheck-only targetであり、CL/Vを自動的に再較正しません。`
            : `This fixture treats CL=${metricNumber(derived.CL_abs_L_per_h_at_70kg)} L/h and V=${metricNumber(derived.V_abs_L_at_70kg)} L as the independent one-compartment parameters. The reported t½ of ${metricNumber(parsed.half_life_h)} h remains a downstream check-only target and does not automatically recalibrate CL/V.`}
        </p>
        <div className="decision-grid">
          <div>
            <span>{t.basis}</span>
            <strong>{formatValue(parsed.clearance_basis, lang)} / {formatValue(parsed.volume_basis, lang)}</strong>
          </div>
          <div>
            <span>ke = CL/V</span>
            <strong>{metricNumber(derived.ke_1_per_h)} 1/h</strong>
          </div>
          <div>
            <span>{lang === "ja" ? "モデル暗黙t½" : "Model-implied t½"}</span>
            <strong>{modelHalfLife ? `${modelHalfLife.toFixed(2)} h` : "—"}</strong>
          </div>
        </div>
      </section>

      <section className="panel chain-panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">AUDIT TRAIL</span>
            <h2>{t.evidenceChain}</h2>
          </div>
        </div>
        <div className="chain">
          {[
            ["01", t.raw, t.rawHint, drug.raw],
            ["02", t.parsed, t.parsedHint, drug.parsed],
            ["03", t.derived, t.derivedHint, drug.derived],
            ["04", t.model, t.modelHint, theta],
          ].map(([step, title, hint, value]) => (
            <div className="chain-step" key={String(step)}>
              <div className="chain-index">{step}</div>
              <div className="chain-copy">
                <h3>{title}</h3>
                <p>{hint}</p>
                <div className="chain-value">{shortText(value, lang, 260)}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">PARAMETER LEDGER</span>
            <h2>{t.parameterTable}</h2>
          </div>
        </div>
        <p className="table-scroll-hint">{t.tableScrollHint}</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>{t.parameter}</th><th>{t.value}</th><th>{t.sourceField}</th><th>{t.calculation}</th><th>{t.status}</th></tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key}>
                  <th>{row.key}</th>
                  <td className="value-cell">{row.value}</td>
                  <td><code>{row.source}</code></td>
                  <td>{row.note}</td>
                  <td><span className={row.status === "確認済み" || row.status === "Checked" ? "mini-status good" : "mini-status warning"}>{row.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <EvidenceAudit drug={drug} lang={lang} />

      <div className="two-column">
        <SourceList drug={drug} lang={lang} />
        <section className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">TARGET REVIEW</span>
              <h2>{t.targetChecks}</h2>
            </div>
          </div>
          <div className="target-list">
            {Object.entries(targets.targets ? record(targets.targets) : {}).map(([key, target]) => {
              const item = record(target);
              return (
                <div className="target-item" key={key}>
                  <div><strong>{key}</strong><span>{formatValue(item.role, lang) || t.unknown}</span></div>
                  <b>{formatValue(item.value, lang)} {formatValue(item.unit, lang)}</b>
                  <p>{shortText(item.summary || item.basis || item.target_basis, lang, 170)}</p>
                </div>
              );
            })}
            {!Object.keys(targets.targets ? record(targets.targets) : {}).length && <p className="muted-text">—</p>}
          </div>
          {mismatch.acknowledged === true && (
            <div className="notice warning-notice">
              <strong>{t.mismatch}</strong>
              <span>{t.acknowledged}{mismatchPercent ? ` · ${mismatchPercent.toFixed(1)}%` : ""}</span>
            </div>
          )}
        </section>
      </div>

      <div className="two-column">
        <section className="panel pharmacology-panel">
          {(() => {
            const pharmacology = drug.pharmacology ?? { status: "not_curated", claim_count: 0, claims: [] };
            const pharmacologyClaims = pharmacology.claims ?? [];
            const pharmacologyReviewed = pharmacology.status === "curated";
            const pharmacologyStatus = pharmacology.status === "curated"
              ? t.pharmacologyCurated
              : pharmacology.status === "partial"
                ? t.pharmacologyPartial
                : lang === "ja" ? "未登録" : "Not registered";
            return (
              <>
          <div className="section-heading">
            <div>
              <span className="eyebrow">PHARMACOLOGY LAYER</span>
              <h2>{t.pharmacology}</h2>
            </div>
            <span className={`status ${pharmacology.status === "curated" ? "good" : pharmacology.status === "partial" ? "context" : "muted"}`}>{pharmacologyStatus}</span>
          </div>
          <p>{pharmacologyReviewed ? t.pharmacologyReviewedContext : t.pharmacologyPending}</p>
          {pharmacologyClaims.length ? (
            <div className="pharmacology-claim-list">
              {pharmacologyClaims.map((claim) => (
                <article className="pharmacology-claim" key={claim.claim_id}>
                  <div className="pharmacology-claim-heading">
                    <strong>{claim.claim_type}</strong>
                    <span className={`mini-status ${claim.evidence_level === "reviewed" ? "good" : "warning"}`}>{claim.evidence_level === "reviewed" ? t.pharmacologyCurated : t.pharmacologySourceCandidate}</span>
                  </div>
                  <p className="pharmacology-statement">{localizedText(claim.statement, lang, 240)}</p>
                  {claim.evidence_summary && <p className="evidence-summary-text">{localizedText(claim.evidence_summary, lang, 210)}</p>}
                  <div className="pharmacology-meta">
                    <span>{t.pharmacologyClaimStatus}: {claim.claim_status === "reviewed" ? t.pharmacologyCurated : t.unknown}</span>
                    <span>{t.pharmacologySourceFit}: {claim.source_fit_status === "reviewed" ? t.pharmacologyCurated : t.unknown}</span>
                  </div>
                  {claim.exact_quote && <blockquote className="pharmacology-quote">“{claim.exact_quote}”</blockquote>}
                  {claim.source_locator && <div className="pharmacology-locator"><span>{t.sourceLocator}:</span> {claim.source_locator}</div>}
                  {claim.source?.url ? (
                    <a className="pharmacology-source" href={claim.source.url} target="_blank" rel="noreferrer">
                      {claim.source_key ?? claim.source.display_id} · {claim.source.kind ?? "source"}<span aria-hidden="true"> ↗</span>
                    </a>
                  ) : <span className="muted-text">{t.noSource}</span>}
                  {claim.missing.length > 0 && (
                    <div className="pharmacology-missing"><span>{t.pharmacologyMissing}</span>{claim.missing.join(", ")}</div>
                  )}
                </article>
              ))}
            </div>
          ) : <p className="muted-text">{t.pharmacologyNoClaims}</p>}
          <div className="source-chip-row">
            {[...new Set(pharmacologyClaims.map((claim) => claim.source?.kind).filter(Boolean))].map((kind) => <span key={kind}>{kind}</span>)}
          </div>
              </>
            );
          })()}
        </section>
        <section className="panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">SPEC CONTRACT</span>
              <h2>{lang === "ja" ? "実行spec" : "Execution spec"}</h2>
            </div>
          </div>
          <dl className="compact-list">
            <div><dt>{lang === "ja" ? "ファイル" : "File"}</dt><dd>{formatValue(spec.file, lang)}</dd></div>
            <div><dt>{lang === "ja" ? "theta" : "theta"}</dt><dd>{shortText(theta, lang, 160)}</dd></div>
            <div><dt>{lang === "ja" ? "IIV" : "IIV"}</dt><dd>{shortText(spec.iiv, lang, 160)}</dd></div>
            <div><dt>{lang === "ja" ? "残差誤差" : "Residual"}</dt><dd>{shortText(spec.residual, lang, 160)}</dd></div>
          </dl>
        </section>
      </div>

      <footer className="detail-footer">
        <span>{t.notClinical}</span>
        <span>source: {drug.slug}/pk.yml</span>
      </footer>
    </article>
  );
}

function Catalog({
  bundle,
  lang,
  query,
  setQuery,
  route,
  setRoute,
  onOpen,
}: {
  bundle: DrugBundle;
  lang: Language;
  query: string;
  setQuery: (value: string) => void;
  route: string;
  setRoute: (value: string) => void;
  onOpen: (slug: string) => void;
}) {
  const t = copy[lang];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return bundle.drugs.filter((drug) => {
      const matchesRoute = route === "all" || routeCode(drug.route) === route;
      if (!matchesRoute) return false;
      if (!needle) return true;
      const haystack = JSON.stringify(drug).toLowerCase();
      return haystack.includes(needle);
    });
  }, [bundle.drugs, query, route]);
  const oralCount = bundle.drugs.filter((drug) => routeCode(drug.route) === "po").length;
  const sublingualCount = bundle.drugs.filter((drug) => routeCode(drug.route) === "sl").length;
  const ivCount = bundle.drugs.filter((drug) => routeCode(drug.route) === "iv").length;
  const sourceCount = bundle.drugs.reduce((sum, drug) => sum + drug.sources.length, 0);
  const reviewCount = bundle.drugs.filter((drug) => hasOpenReview(drug)).length;
  const citationNoteCount = bundle.drugs.filter((drug) => !hasOpenReview(drug) && hasCitationGap(drug)).length;
  const pharmacologyClaimCount = bundle.drugs.reduce((sum, drug) => sum + (drug.pharmacology.claim_count ?? 0), 0);
  const pharmacologyReviewedCount = bundle.drugs.reduce((sum, drug) => sum + (drug.pharmacology.reviewed_count ?? 0), 0);
  const pharmacologyCandidateCount = pharmacologyClaimCount - pharmacologyReviewedCount;

  return (
    <div className="catalog-view">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">{t.kicker}</span>
          <h1>{t.title}</h1>
          <p>{t.intro}</p>
          <div className="hero-note"><span className="dot" /> {t.notClinical}</div>
          <div className="hero-note readiness-note"><span className="dot" /> {lang === "ja"
            ? `最新監査: ${parameterAudit.drug_count}薬剤・${parameterAudit.core_parameter_count}項目。臨床モデル採用は全薬剤で保留です。`
            : `Latest audit: ${parameterAudit.drug_count} drugs, ${parameterAudit.core_parameter_count} parameters. Clinical model use remains on hold.`}</div>
          <a className="mobile-catalog-jump" href="#catalog-section">{t.mobileCatalogJump} →</a>
        </div>
        <div className="hero-stamp">
          <span>v0.1</span>
          <strong>{bundle.drug_count}</strong>
          <small>{t.drugs}</small>
        </div>
      </section>

      <AuditPanel lang={lang} />

      <div className="metrics">
        <div className="metric-card accent-blue"><span>{t.drugs}</span><strong>{bundle.drug_count}</strong><small>canonical YAML records</small></div>
        <div className="metric-card accent-teal"><span>{t.oral}</span><strong>{oralCount}</strong><small>route: po</small></div>
        <div className="metric-card accent-gold"><span>{t.sublingual}</span><strong>{sublingualCount}</strong><small>route: sl</small></div>
        <div className="metric-card accent-blue"><span>{t.iv}</span><strong>{ivCount}</strong><small>route: iv</small></div>
        <div className="metric-card accent-purple"><span>{t.sourceCount}</span><strong>{sourceCount}</strong><small>{reviewCount} {t.needsReview.toLowerCase()}{citationNoteCount ? ` · ${citationNoteCount} ${t.citationGap.toLowerCase()}` : ""}</small></div>
        <div className="metric-card accent-gold"><span>{t.pharmacologyMetric}</span><strong>{pharmacologyReviewedCount}/{pharmacologyClaimCount}</strong><small>{lang === "ja" ? `確認済み${pharmacologyReviewedCount}件 · 原典候補${pharmacologyCandidateCount}件` : `${pharmacologyReviewedCount} reviewed · ${pharmacologyCandidateCount} source candidates`}</small></div>
      </div>

      <section className="about-strip" id="about">
        <div className="about-heading">
          <span className="eyebrow">HOW TO READ</span>
          <h2>{t.aboutTitle}</h2>
          <p>{t.aboutIntro}</p>
        </div>
        <ol className="about-steps">
          <li><span>01</span><div><strong>{t.aboutSourceTitle}</strong><p>{t.aboutSourceText}</p></div></li>
          <li><span>02</span><div><strong>{t.aboutDerivedTitle}</strong><p>{t.aboutDerivedText}</p></div></li>
          <li><span>03</span><div><strong>{t.aboutModelTitle}</strong><p>{t.aboutModelText}</p></div></li>
        </ol>
      </section>

      <section className="catalog-section" id="catalog-section">
        <div className="catalog-heading">
          <div><span className="eyebrow">CATALOG</span><h2>{t.catalog}</h2><p>{t.catalogIntro}</p></div>
          <div className="catalog-controls">
            <label className="search-box"><span aria-hidden="true">⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t.search} aria-label={t.search} /></label>
            <select value={route} onChange={(event) => setRoute(event.target.value)} aria-label={t.route}>
              <option value="all">{t.allRoutes}</option><option value="po">{t.oral}</option><option value="sl">{t.sublingual}</option><option value="iv">{t.iv}</option>
            </select>
          </div>
        </div>
        <div className="catalog-result-line"><span>{filtered.length} / {bundle.drugs.length} {t.drugs}</span><span>{t.language}: {lang === "ja" ? t.japanese : t.english}</span></div>
        {filtered.length ? (
          <div className="drug-grid">
            {filtered.map((drug) => {
              const parsed = record(drug.parsed);
              const derived = record(drug.derived);
              return (
                <button className="drug-card" key={drug.slug} onClick={() => onOpen(drug.slug)} type="button">
                  <div className="drug-card-top"><span className="route-badge">{routeLabel(drug.route, lang)}</span><span className={statusClass(drug)}>{statusForDrug(drug, lang)}</span></div>
                  <h3>{drug.name}</h3><p className="slug">{drug.slug}</p>
                  <div className={`pharmacology-card-status ${pharmacologyStatusClass(drug)}`}><span aria-hidden="true" />{pharmacologyStatusForDrug(drug, lang)}</div>
                  <div className="drug-card-values"><div><span>CL</span><strong>{metricNumber(derived.CL_abs_L_per_h_at_70kg)}</strong><small>L/h</small></div><div><span>V</span><strong>{metricNumber(derived.V_abs_L_at_70kg)}</strong><small>L</small></div><div><span>t½</span><strong>{metricNumber(parsed.half_life_h)}</strong><small>h</small></div></div>
                  <div className="drug-card-footer"><span>{drug.sources.length} {t.sourceCount} · {drug.evidence.summary.unresolved_count} {t.unresolvedEvidence}</span><span className="view-link">{lang === "ja" ? "根拠を見る" : "View evidence"} →</span></div>
                </button>
              );
            })}
          </div>
        ) : <div className="empty-state">{t.noResults}</div>}
      </section>
    </div>
  );
}

export default function Home() {
  const [bundle] = useState<DrugBundle>(initialBundle);
  const [lang, setLang] = useState<Language>("ja");
  const [query, setQuery] = useState("");
  const [route, setRoute] = useState("all");
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);

  useEffect(() => {
    const syncHash = () => {
      const value = window.location.hash.match(/^#drug=([^&]+)/)?.[1];
      setSelectedSlug((current) => value
        ? decodeURIComponent(value)
        : window.location.hash === "" ? null : current);
    };
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  const openDrug = (slug: string) => { window.location.hash = `drug=${encodeURIComponent(slug)}`; };
  const backToCatalog = () => { window.location.hash = ""; window.scrollTo({ top: 0, behavior: "smooth" }); };
  const selected = bundle?.drugs.find((drug) => drug.slug === selectedSlug) ?? null;
  const t = copy[lang];

  return (
    <div className="site-shell">
      <aside className="sidebar">
        <button className="brand" onClick={backToCatalog} type="button"><span className="brand-mark">PK</span><span><strong>{t.brand}</strong><small>source-linked docs</small></span></button>
        <nav className="side-nav" aria-label="Documentation navigation"><button className={!selected ? "active" : ""} onClick={backToCatalog} type="button"><span>⌂</span>{t.catalog}</button><a href="#about"><span>◎</span>{t.readGuide}</a></nav>
        <div className="sidebar-rule" />
        <div className="sidebar-note"><span className="eyebrow">SOURCE POLICY</span><p>{lang === "ja" ? "URLの存在だけでは値単位の直接根拠とみなしません。確認済み・導出・fixture仮定・未確認を分けて表示します。" : "A URL alone is not treated as value-level evidence. Checked, derived, fixture-policy, and unconfirmed claims stay separate."}</p></div>
        <div className="sidebar-foot"><span>PKDUMMY-HARNESS</span><span>2026 · bilingual</span></div>
      </aside>
      <main className="main-content">
        <header className="topbar"><div className="breadcrumbs"><span>docs</span><span>/</span><strong>{selected ? selected.slug : "index"}</strong></div><div className="top-actions"><a className="mobile-about-link" href="#about">{t.readGuide}</a><span className="lang-label">{t.language}</span><button className={lang === "ja" ? "lang active" : "lang"} onClick={() => setLang("ja")} type="button">日本語</button><button className={lang === "en" ? "lang active" : "lang"} onClick={() => setLang("en")} type="button">EN</button></div></header>
        {selected ? <DetailView drug={selected} lang={lang} onBack={backToCatalog} /> : <Catalog bundle={bundle} lang={lang} query={query} setQuery={setQuery} route={route} setRoute={setRoute} onOpen={openDrug} />}
      </main>
    </div>
  );
}
