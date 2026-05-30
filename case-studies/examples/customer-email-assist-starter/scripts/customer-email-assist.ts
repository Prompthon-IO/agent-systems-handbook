#!/usr/bin/env tsx

import fs from "node:fs";
import path from "node:path";

import { deleteDatabaseFiles, openDatabase, resolveDbPath } from "@/lib/db";
import { GoogleGmailAdapter } from "@/lib/gmail";
import {
  applySendQueue,
  createIssueFromUnderstanding,
  createUnderstandingFromPreparedItem,
  importPreparedInboundBatch,
  prepareDraftBatch,
  prepareInboundBatch,
  renderAndSaveDrafts,
} from "@/lib/sync";
import type {
  DraftRenderRecord,
  DraftTemplateFields,
  PreparedInboundItem,
  UnderstandingRecord,
} from "@/lib/types";

function usage(): never {
  throw new Error(
    [
      "Usage: tsx scripts/customer-email-assist.ts <command> [options]",
      "Commands:",
      "  init-db [--fresh]",
      "  setup-local",
      "  apply-send-queue",
      "  prepare-inbound-batch [--out <file>]",
      "  import-prepared-batch --input <file> [--policy <file>]",
      "  persist-understanding --input <file>",
      "  prepare-draft-batch [--policy <file>] [--out <file>]",
      "  render-save-drafts --input <file>",
      "  sync [--policy <file>]",
    ].join("\n"),
  );
}

function optionValue(flag: string): string | undefined {
  const index = process.argv.indexOf(flag);
  if (index === -1) {
    return undefined;
  }
  return process.argv[index + 1];
}

function hasFlag(flag: string): boolean {
  return process.argv.includes(flag);
}

function outputValue(): string | undefined {
  return optionValue("--out");
}

function emitJson(payload: unknown): void {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function emitOrWriteJson(payload: unknown, label: string): void {
  const outputPath = outputValue();
  if (!outputPath) {
    emitJson(payload);
    return;
  }

  const resolved = path.resolve(outputPath);
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  fs.writeFileSync(resolved, JSON.stringify(payload));
  const count =
    payload && typeof payload === "object" && "items" in payload && Array.isArray(payload.items)
      ? payload.items.length
      : Array.isArray(payload)
        ? payload.length
        : undefined;
  emitJson({
    ok: true,
    label,
    outputPath: resolved,
    count,
  });
}

function readJsonFile<T>(inputPath: string | undefined): T {
  if (!inputPath) {
    throw new Error("Missing required --input <file> option.");
  }
  return JSON.parse(fs.readFileSync(path.resolve(inputPath), "utf8")) as T;
}

function readPreparedInboundItems(inputPath: string | undefined): PreparedInboundItem[] {
  const parsed = readJsonFile<PreparedInboundItem[] | { items: PreparedInboundItem[] }>(inputPath);
  return Array.isArray(parsed) ? parsed : parsed.items;
}

function fallbackDraftFields(record: {
  customerName: string;
  classification: DraftTemplateFields["classification"];
  policyEvidence: string[];
}): Omit<DraftTemplateFields, "classification"> {
  const genericStep =
    record.classification === "handoff_required"
      ? "A human reviewer will follow up after checking the policy and account details."
      : "Please reply with any missing order or account details so the team can continue.";

  const acknowledgement =
    record.classification === "refund_request"
      ? "I understand that you received the wrong item and are asking for a refund."
      : record.classification === "billing_issue"
        ? "I understand that you need help with a billing or invoice question."
        : record.classification === "complaint"
          ? "I understand that you are unhappy with the recent support experience."
          : record.classification === "handoff_required"
            ? "I understand that this request requires additional review."
            : "I understand that you have a support question.";

  return {
    customerName: record.customerName,
    acknowledgement,
    nextStep: genericStep,
    policyEvidence: record.policyEvidence,
    signoff: "Support Team",
  };
}

async function main() {
  const command = process.argv[2];
  if (!command) {
    usage();
  }

  switch (command) {
    case "init-db": {
      if (hasFlag("--fresh")) {
        deleteDatabaseFiles();
      }
      const db = openDatabase();
      db.close();
      emitJson({
        ok: true,
        dbPath: resolveDbPath(),
        fresh: hasFlag("--fresh"),
      });
      return;
    }

    case "setup-local": {
      deleteDatabaseFiles();
      const db = openDatabase();
      db.close();
      emitJson({
        ok: true,
        dbPath: resolveDbPath(),
        fresh: true,
        next: ["npm run dev"],
      });
      return;
    }

    case "apply-send-queue": {
      const db = openDatabase();
      const gmail = new GoogleGmailAdapter();
      const result = await applySendQueue(db, gmail);
      db.close();
      emitJson(result);
      return;
    }

    case "prepare-inbound-batch": {
      const db = openDatabase();
      const gmail = new GoogleGmailAdapter();
      const batch = await prepareInboundBatch(db, gmail);
      db.close();
      emitOrWriteJson(batch, "preparedInboundBatch");
      return;
    }

    case "persist-understanding": {
      const db = openDatabase();
      const records = readJsonFile<UnderstandingRecord[]>(optionValue("--input"));
      const issueIds = records.map((record) => createIssueFromUnderstanding(db, record).issueId);
      db.close();
      emitJson({ ok: true, issueIds });
      return;
    }

    case "import-prepared-batch": {
      const db = openDatabase();
      const items = readPreparedInboundItems(optionValue("--input"));
      const imported = importPreparedInboundBatch(db, items);
      const issueIdSet = new Set(imported.issueIds);
      const draftBatch = prepareDraftBatch(db, optionValue("--policy"));
      const draftRecords: DraftRenderRecord[] = draftBatch.items
        .filter((item) => issueIdSet.has(item.issueId))
        .map((item) => ({
          issueId: item.issueId,
          classification: item.classification,
          draftFields: fallbackDraftFields(item),
        }));
      renderAndSaveDrafts(db, draftRecords);
      db.close();
      emitJson({
        ok: true,
        importedCount: items.length,
        issueIds: imported.issueIds,
        renderedDrafts: draftRecords.length,
      });
      return;
    }

    case "prepare-draft-batch": {
      const db = openDatabase();
      const batch = prepareDraftBatch(db, optionValue("--policy"));
      db.close();
      emitOrWriteJson(batch, "preparedDraftBatch");
      return;
    }

    case "render-save-drafts": {
      const db = openDatabase();
      const records = readJsonFile<DraftRenderRecord[]>(optionValue("--input"));
      renderAndSaveDrafts(db, records);
      db.close();
      emitJson({ ok: true, count: records.length });
      return;
    }

    case "sync": {
      const db = openDatabase();
      const gmail = new GoogleGmailAdapter();
      const applyResult = await applySendQueue(db, gmail);
      const inboundBatch = await prepareInboundBatch(db, gmail);
      const understandings = inboundBatch.items.map((item) => createUnderstandingFromPreparedItem(item));
      understandings.forEach((record) => {
        createIssueFromUnderstanding(db, record);
      });
      const draftBatch = prepareDraftBatch(db, optionValue("--policy"));
      const draftRecords: DraftRenderRecord[] = draftBatch.items.map((item) => ({
        issueId: item.issueId,
        classification: item.classification,
        draftFields: fallbackDraftFields(item),
      }));
      renderAndSaveDrafts(db, draftRecords);
      db.close();
      emitJson({
        ok: true,
        sendQueue: applyResult,
        inboundCount: inboundBatch.items.length,
        persistedIssues: understandings.length,
        renderedDrafts: draftRecords.length,
      });
      return;
    }

    default:
      usage();
  }
}

void main();
