import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CsvTab } from "../features/intake/CsvTab";
import DuplicatesPage from "../features/duplicates/DuplicatesPage";
import { csvIntakeApi } from "../lib/csvIntake";
import { duplicatesApi } from "../lib/duplicates";

describe("M4.2 CSV and duplicate-review UI", () => {
  afterEach(() => jest.restoreAllMocks());

  it("shows server formula warnings and submits the original selected file", async () => {
    const file = new File(["address_line,suburb,state\n1 Test St,Subiaco,WA"], "rows.csv", { type: "text/csv" });
    const preview = jest.spyOn(csvIntakeApi, "preview").mockResolvedValue({
      batch_key: "b".repeat(64), filename: "rows.csv", total_rows: 1, valid_rows: 1,
      warning_rows: 1, error_rows: 0, headers_found: ["address_line", "suburb", "state"], headers_missing: [],
      preview_rows: [{ row_index: 0, address_line: "1 Test St", suburb: "Subiaco", state: "WA", errors: [], warnings: ["Formula-like"], formula_flags: ["notes"], skippable: false, status: "warning" }],
    });
    const imported = jest.spyOn(csvIntakeApi, "import").mockResolvedValue({
      batch_id: "batch", batch_key: "b".repeat(64), filename: "rows.csv", state: "completed", total_rows: 1,
      created: 1, matched_existing: 0, requires_review: 0, failed: 0, skipped: 0, row_results: [],
    });
    render(<CsvTab journeyId="journey-1" />);
    fireEvent.change(screen.getByTestId("csv-file-input"), { target: { files: [file] } });
    expect(await screen.findByTestId("csv-preview-panel")).toBeInTheDocument();
    expect(screen.getByText(/formula-like: notes/i)).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("csv-confirm-import"));
    await waitFor(() => expect(imported).toHaveBeenCalledWith("journey-1", file, []));
    expect(preview).toHaveBeenCalledWith("journey-1", file);
    expect(await screen.findByTestId("csv-batch-result")).toBeInTheDocument();
  });

  it("presents a proposed match and sends a deliberate reject action", async () => {
    const proposal = {
      id: "proposal-1", workspace_id: "workspace-1", state: "pending" as const, proposal_reason: "address_scan",
      evidence: { street_number: "81" }, unit_suffix_warning: true, review_reason: null, actor_user_id: null,
      reviewed_at: null, row_version: 1, created_at: null,
      property_a: { id: "a", address_line: "81A Test Street", suburb: "Nedlands", state: "WA", postcode: "6009", normalised_address: "a", fact_count: 1, created_at: null, earliest_discovery: null, merged_into_id: null },
      property_b: { id: "b", address_line: "81C Test Street", suburb: "Nedlands", state: "WA", postcode: "6009", normalised_address: "b", fact_count: 1, created_at: null, earliest_discovery: null, merged_into_id: null },
    };
    jest.spyOn(duplicatesApi, "list").mockResolvedValue({ items: [proposal], pending_count: 1, total_count: 1 });
    const rejected = jest.spyOn(duplicatesApi, "reject").mockResolvedValue({ ...proposal, state: "rejected", row_version: 2 });
    render(<DuplicatesPage />);
    expect(await screen.findByTestId("dup-proposal-proposal-1")).toBeInTheDocument();
    expect(screen.getByTestId("dup-unit-suffix-warning")).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("dup-action-reject"));
    await waitFor(() => expect(rejected).toHaveBeenCalledWith("proposal-1", 1, undefined));
    expect(screen.getByText("rejected")).toBeInTheDocument();
  });
});