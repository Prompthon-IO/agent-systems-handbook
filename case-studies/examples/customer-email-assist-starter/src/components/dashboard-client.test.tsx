import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DashboardClient } from "@/components/dashboard-client";

const originalFetch = global.fetch;

describe("DashboardClient", () => {
  let issueStatusResponse: string;
  let reviewQueueResponse: {
    items: Array<{
      id: number;
      email: string;
      displayName: string;
      description: string;
      status: string;
      lastSeenAt: string | null;
      issueCount: number;
    }>;
    total: number;
    page: number;
    pageSize: number;
  };
  let customerResponse: {
    items: Array<{
      id: number;
      email: string;
      displayName: string;
      description: string;
      status: string;
      lastSeenAt: string | null;
      issueCount: number;
    }>;
    total: number;
    page: number;
    pageSize: number;
  };

  beforeEach(() => {
    issueStatusResponse = "draft_ready";
    reviewQueueResponse = {
      items: [],
      total: 0,
      page: 1,
      pageSize: 10,
    };
    customerResponse = {
      items: [
        {
          id: 2,
          email: "customer@example.com",
          displayName: "Customer Preview",
          description: "Preferred wholesale buyer",
          status: "approved",
          lastSeenAt: "2026-05-30T10:00:00Z",
          issueCount: 3,
        },
        {
          id: 3,
          email: "ignored@example.com",
          displayName: "Ignored Customer",
          description: "Known noise sender",
          status: "ignored",
          lastSeenAt: "2026-05-29T10:00:00Z",
          issueCount: 1,
        },
      ],
      total: 1,
      page: 1,
      pageSize: 10,
    };

    global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/gmail/oauth/status") {
        return new Response(
          JSON.stringify({
            configured: true,
            connected: false,
            emailAddress: "",
            connectedAt: null,
            usesEnvRefreshToken: false,
          }),
          { status: 200 },
        );
      }
      if (url.startsWith("/api/issues")) {
        if (init?.method === "PATCH") {
          const payload = JSON.parse(String(init.body)) as { action?: string };
          return new Response(
            JSON.stringify({
              ok:
                payload.action === "send_approved" ||
                payload.action === "queue_send" ||
                payload.action === "revoke_send_approval",
              queued: payload.action === "queue_send",
              sent: payload.action === "send_approved",
              manuallyResolved: false,
            }),
            { status: 200 },
          );
        }
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 1,
                customerName: "Casey",
                customerEmail: "casey@example.com",
                classification: "refund_request",
                summary: "Wrong item received",
                urgency: "normal",
                actionSuggestion: "send_reply",
                issueStatus: issueStatusResponse,
                receivedAt: "2026-05-30T12:00:00Z",
                originalMessageText: "The wrong item was delivered.",
                draftReplyHtml: "<p>Draft reply</p>",
                policyEvidence: ["Refunds are available within 30 days."],
              },
            ],
            total: 1,
            page: 1,
            pageSize: 10,
            summaryCounts: {
              total: 1,
              draft_ready: 1,
              approved_to_send: 0,
              resolved: 0,
              sync_error: 0,
            },
          }),
          { status: 200 },
        );
      }
      if (url === "/api/analytics") {
        return new Response(JSON.stringify({ buckets: [] }), { status: 200 });
      }
      if (url.startsWith("/api/customers/review")) {
        if (init?.method === "PATCH") {
          return new Response(JSON.stringify({ ok: true }), { status: 200 });
        }
        return new Response(JSON.stringify(reviewQueueResponse), {
          status: 200,
        });
      }
      if (url.startsWith("/api/customers")) {
        if (init?.method === "PATCH") {
          const payload = JSON.parse(String(init.body)) as { status?: string };
          const id = Number(url.split("/").pop());
          customerResponse = {
            ...customerResponse,
            items: customerResponse.items.map((item) =>
              item.id === id && payload.status
                ? {
                    ...item,
                    status: payload.status,
                  }
                : item,
            ),
          };
          return new Response(JSON.stringify({ ok: true }), { status: 200 });
        }
        const parsed = new URL(url, "http://localhost");
        const statuses = parsed.searchParams.getAll("status");
        const filteredItems =
          statuses.length > 0
            ? customerResponse.items.filter((item) => statuses.includes(item.status))
            : customerResponse.items;
        return new Response(
          JSON.stringify({
            items: filteredItems,
            total: filteredItems.length,
            page: 1,
            pageSize: 10,
          }),
          { status: 200 },
        );
      }
      throw new Error(`Unhandled fetch ${url}`);
    }) as typeof fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.useRealTimers();
  });

  it("opens the issue drawer from a row click and keeps action buttons isolated", async () => {
    const user = userEvent.setup();
    render(<DashboardClient />);

    expect(await screen.findByText("Wrong item received")).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Status" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Review" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve to Send" })).not.toBeInTheDocument();

    await user.click(screen.getByText("Wrong item received"));
    expect(await screen.findByText("Issue Summary")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve & Send" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => {
      expect(screen.queryByText("Issue Summary")).not.toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Mark Resolved" }));
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/issues/1",
        expect.objectContaining({
          method: "PATCH",
        }),
      );
    });
  });

  it("refreshes the dashboard data from the issues toolbar", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(global.fetch);
    render(<DashboardClient />);

    expect(await screen.findByText("Wrong item received")).toBeInTheDocument();
    expect(screen.getByRole("radiogroup", { name: "Gmail mode" })).toBeInTheDocument();
    expect(screen.getByText("OAuth")).toBeInTheDocument();

    const countCalls = (matcher: (url: string) => boolean) =>
      fetchMock.mock.calls.filter(([input]) => matcher(typeof input === "string" ? input : input.toString())).length;

    const issueCallsBefore = countCalls((url) => url.startsWith("/api/issues"));
    const analyticsCallsBefore = countCalls((url) => url.startsWith("/api/analytics"));
    const reviewCallsBefore = countCalls((url) => url.startsWith("/api/customers/review"));
    const customerCallsBefore = countCalls(
      (url) => url.startsWith("/api/customers?") || url === "/api/customers",
    );

    await user.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => {
      expect(countCalls((url) => url.startsWith("/api/issues"))).toBeGreaterThan(issueCallsBefore);
      expect(countCalls((url) => url.startsWith("/api/analytics"))).toBeGreaterThan(analyticsCallsBefore);
      expect(countCalls((url) => url.startsWith("/api/customers/review"))).toBeGreaterThan(reviewCallsBefore);
      expect(countCalls((url) => url.startsWith("/api/customers?") || url === "/api/customers")).toBeGreaterThan(
        customerCallsBefore,
      );
    });
  });

  it("queues drawer send with a countdown and allows cancel before execution", async () => {
    render(<DashboardClient />);

    expect(await screen.findByText("Wrong item received")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Wrong item received"));
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "Approve & Send" }));

    expect(screen.getByText("Reply to Casey approved to send")).toBeInTheDocument();
    expect(screen.getAllByText(/Sending in \d+s\./).length).toBeGreaterThan(0);
    expect(screen.getByText("Status: approved_to_send")).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalledWith(
      "/api/issues/1",
      expect.objectContaining({ method: "PATCH" }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Cancel Send" }));
    expect(screen.queryByText("Reply to Casey approved to send")).not.toBeInTheDocument();
    expect(screen.getByText("Status: draft_ready")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(global.fetch).not.toHaveBeenCalledWith(
      "/api/issues/1",
      expect.objectContaining({ method: "PATCH" }),
    );

    vi.useRealTimers();
  });

  it("executes OAuth send from the drawer after the countdown expires", async () => {
    render(<DashboardClient />);

    expect(await screen.findByText("Wrong item received")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Wrong item received"));
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "Approve & Send" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    await Promise.resolve();

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/issues/1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          draftReplyHtml: "<p>Draft reply</p>",
          action: "send_approved",
        }),
      }),
    );

    vi.useRealTimers();
  });

  it("queues connector send when the Gmail connector switch is enabled", async () => {
    render(<DashboardClient />);

    expect(await screen.findByText("Wrong item received")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Gmail connector"));
    expect(screen.getByRole("radiogroup", { name: "Gmail mode" })).toBeInTheDocument();

    fireEvent.click(screen.getByText("Wrong item received"));
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "Approve for Connector" }));
    expect(screen.getAllByText(/Queuing for connector in \d+s\./).length).toBeGreaterThan(0);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    await Promise.resolve();

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/issues/1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          draftReplyHtml: "<p>Draft reply</p>",
          action: "queue_send",
        }),
      }),
    );

    vi.useRealTimers();
  });

  it("does not allow an approved issue to be approved again", async () => {
    issueStatusResponse = "approved_to_send";
    render(<DashboardClient />);

    expect(await screen.findByText("Wrong item received")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Wrong item received"));

    expect(await within(screen.getByRole("dialog")).findByText("Approved to send")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approved to Send" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Approve & Send" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel Approval" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel Approval" }));
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/issues/1",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ action: "revoke_send_approval" }),
        }),
      );
    });
  });

  it("shows a customer review button only when pending review customers exist and opens the drawer", async () => {
    const user = userEvent.setup();
    reviewQueueResponse = {
      items: [
        {
          id: 10,
          email: "review@example.com",
          displayName: "Review Me",
          description: "needs verification",
          status: "pending",
          lastSeenAt: null,
          issueCount: 1,
        },
      ],
      total: 1,
      page: 1,
      pageSize: 10,
    };

    render(<DashboardClient />);

    await user.click(await screen.findByRole("tab", { name: "Customers" }));
    expect(await screen.findByRole("button", { name: "Customer Review (1)" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Customer Review (1)" }));

    expect(await screen.findByText("review@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ignore" })).toBeInTheDocument();
  });

  it("opens a customer drawer from row click and keeps delete as an isolated action", async () => {
    const user = userEvent.setup();
    render(<DashboardClient />);

    await user.click(await screen.findByRole("tab", { name: "Customers" }));
    expect(await screen.findByText("Customer Preview")).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Status" })).not.toBeInTheDocument();
    expect(screen.queryByText("Ignored Customer")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();

    await user.click(screen.getByText("Customer Preview"));
    expect(await screen.findByText("Customer Summary")).toBeInTheDocument();
    expect(within(screen.getByRole("dialog")).getByText("Preferred wholesale buyer")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => {
      expect(screen.queryByText("Customer Summary")).not.toBeInTheDocument();
    });

    await user.click(screen.getByRole("switch", { name: "Allow customer" }));
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/customers/2",
        expect.objectContaining({
          method: "PATCH",
        }),
      );
    });
    expect(screen.queryByText("Customer Preview")).not.toBeInTheDocument();
  });

  it("shows ignored customers only when requested", async () => {
    const user = userEvent.setup();
    render(<DashboardClient />);

    await user.click(await screen.findByRole("tab", { name: "Customers" }));
    expect(await screen.findByText("Customer Preview")).toBeInTheDocument();
    expect(screen.queryByText("Ignored Customer")).not.toBeInTheDocument();

    await user.click(screen.getByRole("switch", { name: "Show ignored" }));

    expect(await screen.findByText("Ignored Customer")).toBeInTheDocument();
  });
});
