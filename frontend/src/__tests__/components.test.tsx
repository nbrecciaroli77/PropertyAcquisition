import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { CompareRow } from "../components/CompareRow";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { EvidenceState } from "../components/EvidenceState";
import { FitRing } from "../components/FitRing";
import { PropertyCard } from "../components/PropertyCard";
import { freshnessBand, SourceFreshness } from "../components/SourceFreshness";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { StatusChip } from "../components/StatusChip";
import { known, unknown } from "../lib/format";
import { properties } from "../lib/synthetic";

describe("shared components — semantics", () => {
  it("StatusChip conveys status with text and icon, never colour alone", () => {
    render(<StatusChip tone="fail" data-testid="chip">Fail</StatusChip>);
    const chip = screen.getByTestId("chip");
    expect(chip).toHaveAttribute("data-tone", "fail");
    expect(chip).toHaveTextContent("Fail");
    expect(within(chip).getByTestId("chip-icon")).toBeInTheDocument();
  });

  it("EvidenceState keeps Unknown distinct from Fail", () => {
    render(
      <>
        <EvidenceState outcome="Unknown" data-testid="u" />
        <EvidenceState outcome="Fail" data-testid="f" />
      </>,
    );
    expect(screen.getByTestId("u")).toHaveAttribute("data-outcome", "Unknown");
    expect(screen.getByTestId("u")).toHaveTextContent(/unknown is not pass/i);
    expect(screen.getByTestId("f")).toHaveAttribute("data-outcome", "Fail");
    expect(screen.getByTestId("f")).not.toHaveTextContent(/unknown/i);
  });

  it("FitRing renders unavailable for unknown, never 0%", () => {
    render(<FitRing value={unknown()} label="Provisional fit" data-testid="ring" />);
    expect(screen.getByTestId("ring")).toHaveAttribute("data-state", "unknown");
    expect(screen.getByRole("img", { name: /provisional fit unavailable/i })).toBeInTheDocument();
    expect(screen.queryByText("0%")).toBeNull();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });

  it("FitRing renders a known percentage", () => {
    render(<FitRing value={known(82)} label="Provisional fit" />);
    expect(screen.getByRole("img", { name: /82 percent/i })).toBeInTheDocument();
  });

  it("CompareRow shows Unknown as a labelled state, not a dash", () => {
    render(<CompareRow attribute="Land size" columns={["A", "B"]} cells={[{ value: "420 m²" }, { value: "", state: "unknown" }]} />);
    const cells = screen.getAllByRole("cell");
    expect(cells[0]).toHaveTextContent("420 m²");
    expect(cells[1]).toHaveAttribute("data-state", "unknown");
    expect(cells[1]).toHaveTextContent("Unknown");
    expect(cells[1]).not.toHaveTextContent("—");
  });

  it("SourceFreshness bands by age and shows a time element", () => {
    const now = new Date("2026-06-20T00:00:00+08:00");
    expect(freshnessBand("2026-06-19T00:00:00+08:00", now)).toBe("fresh");
    expect(freshnessBand("2026-06-15T00:00:00+08:00", now)).toBe("ageing");
    expect(freshnessBand("2026-06-01T00:00:00+08:00", now)).toBe("stale");
    render(<SourceFreshness source="Manual entry" checkedAt="2026-06-01T00:00:00+08:00" now={now} data-testid="fresh" />);
    expect(screen.getByTestId("fresh")).toHaveAttribute("data-band", "stale");
    expect(screen.getByText(/checked 1 jun 2026/i)).toBeInTheDocument();
  });

  it("PropertyCard shows raw guide, separate market/buyer state and unknown land for 81C", () => {
    const p81c = properties.find((p) => p.legacyRef === "DEMO-006")!;
    render(
      <MemoryRouter>
        <PropertyCard property={p81c} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("property-card-price-demo-006")).toHaveTextContent("Expressions of interest");
    expect(screen.getByTestId("property-card-market-demo-006")).toHaveTextContent("Market: Active");
    expect(screen.getByTestId("property-card-buyer-demo-006")).toHaveTextContent("You: Reviewing");
    expect(screen.getByTestId("property-card-fit-demo-006")).toHaveAttribute("data-state", "unknown");
    expect(screen.getAllByText("Unknown").length).toBeGreaterThanOrEqual(1);
  });

  it("81A and 81C are separate properties in the fixture", () => {
    const ids = properties.filter((p) => p.address.startsWith("81")).map((p) => p.legacyRef);
    expect(ids).toEqual(["DEMO-005", "DEMO-006"]);
  });

  it("Empty, Error and Skeleton states expose roles", () => {
    render(
      <>
        <EmptyState title="Nothing" description="Genuinely empty" />
        <ErrorState description="Check failed" onRetry={() => undefined} />
        <Skeleton className="h-4" />
      </>,
    );
    expect(screen.getAllByRole("status").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("alert")).toHaveTextContent("Check failed");
    expect(screen.getByTestId("error-state-retry")).toBeInTheDocument();
  });

  it("ConfirmDialog requires explicit confirmation", async () => {
    const onConfirm = jest.fn();
    render(<ConfirmDialog title="Add a reminder?" description="Does not book." confirmLabel="Add reminder" onConfirm={onConfirm} trigger={<button>Open</button>} />);
    await userEvent.click(screen.getByText("Open"));
    expect(screen.getByRole("dialog", { name: "Add a reminder?" })).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("confirm-dialog-cancel"));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText("Open")).toHaveFocus();
    await userEvent.click(screen.getByText("Open"));
    await userEvent.click(screen.getByTestId("confirm-dialog-confirm"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});
