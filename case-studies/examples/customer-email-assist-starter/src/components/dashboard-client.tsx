"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  CheckCircleOutlined,
  ReloadOutlined,
  StopOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Drawer,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";

import { RichTextEditor } from "@/components/rich-text-editor";

const { Title, Text, Paragraph } = Typography;

type IssueItem = {
  id: number;
  customerName: string;
  customerEmail: string;
  classification: string;
  summary: string;
  urgency: string;
  actionSuggestion: string;
  issueStatus: string;
  receivedAt: string;
  originalMessageText?: string;
  draftReplyHtml?: string | null;
  draftReplyText?: string | null;
  policyEvidence?: string[];
};

type IssuesResponse = {
  items: IssueItem[];
  total: number;
  page: number;
  pageSize: number;
  summaryCounts: Record<string, number>;
};

type CustomerItem = {
  id: number;
  email: string;
  displayName: string;
  description: string;
  status: string;
  lastSeenAt: string | null;
  issueCount: number;
};

type CustomerResponse = {
  items: CustomerItem[];
  total: number;
  page: number;
  pageSize: number;
};

type AnalyticsResponse = {
  typeCounts: Array<{ classification: string; count: number }>;
  statusCounts: Array<{ issueStatus: string; count: number }>;
  buckets: Array<{ day: string; classification: string; issueStatus: string; count: number }>;
};

type SendMode = "oauth" | "connector";

type PendingSend = {
  issueId: number;
  label: string;
  draftHtml: string;
  mode: SendMode;
  expiresAt: number;
  previousStatus: string;
};

type PatchIssueResponse = {
  ok: boolean;
  queued?: boolean;
  sent?: boolean;
  manuallyResolved?: boolean;
  sendMode?: "connector_required";
  error?: string;
};

type GmailOAuthStatus = {
  configured: boolean;
  connected: boolean;
  emailAddress: string;
  connectedAt: string | null;
  usesEnvRefreshToken: boolean;
};

const EMPTY_ISSUES: IssuesResponse = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 10,
  summaryCounts: {
    total: 0,
    draft_ready: 0,
    approved_to_send: 0,
    resolved: 0,
    sync_error: 0,
  },
};

const EMPTY_CUSTOMERS: CustomerResponse = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 10,
};

const EMPTY_ANALYTICS: AnalyticsResponse = {
  typeCounts: [],
  statusCounts: [],
  buckets: [],
};

const EMPTY_GMAIL_OAUTH_STATUS: GmailOAuthStatus = {
  configured: false,
  connected: false,
  emailAddress: "",
  connectedAt: null,
  usesEnvRefreshToken: false,
};

const ACTION_DELAY_MS = 5000;

async function fetchJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
}

function toStatusColor(value: string) {
  switch (value) {
    case "approved_to_send":
      return "processing";
    case "resolved":
      return "success";
    case "sync_error":
      return "error";
    case "pending":
      return "warning";
    case "ignored":
      return "default";
    default:
      return "blue";
  }
}

function toClassificationColor(value: string) {
  switch (value) {
    case "complaint":
      return "volcano";
    case "refund_request":
      return "gold";
    case "billing_issue":
      return "cyan";
    case "handoff_required":
      return "magenta";
    case "query":
    default:
      return "blue";
  }
}

function toUrgencyColor(value: string) {
  switch (value) {
    case "high":
      return "red";
    case "normal":
    default:
      return "green";
  }
}

function toActionSuggestionColor(value: string) {
  switch (value) {
    case "manual_follow_up":
      return "orange";
    case "handoff":
      return "magenta";
    case "send_reply":
    default:
      return "green";
  }
}

export function DashboardClient() {
  const [issues, setIssues] = useState<IssuesResponse>(EMPTY_ISSUES);
  const [analytics, setAnalytics] = useState<AnalyticsResponse>(EMPTY_ANALYTICS);
  const [reviewQueue, setReviewQueue] = useState<CustomerResponse>(EMPTY_CUSTOMERS);
  const [customers, setCustomers] = useState<CustomerResponse>(EMPTY_CUSTOMERS);
  const [selectedIssue, setSelectedIssue] = useState<IssueItem | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerItem | null>(null);
  const [draftHtml, setDraftHtml] = useState("");
  const [issueSearch, setIssueSearch] = useState("");
  const [issueClassification, setIssueClassification] = useState<string[]>([]);
  const [issueStatus, setIssueStatus] = useState<string | undefined>();
  const [includeResolved, setIncludeResolved] = useState(false);
  const [customerSearch, setCustomerSearch] = useState("");
  const [showIgnoredCustomers, setShowIgnoredCustomers] = useState(false);
  const [customerDescriptions, setCustomerDescriptions] = useState<Record<number, string>>({});
  const [analyticsStart, setAnalyticsStart] = useState("");
  const [analyticsEnd, setAnalyticsEnd] = useState("");
  const [customerModalOpen, setCustomerModalOpen] = useState(false);
  const [reviewDrawerOpen, setReviewDrawerOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<CustomerItem | null>(null);
  const [pendingSend, setPendingSend] = useState<PendingSend | null>(null);
  const [pendingNow, setPendingNow] = useState(() => Date.now());
  const [refreshingDashboard, setRefreshingDashboard] = useState(false);
  const [gmailConnectorEnabled, setGmailConnectorEnabled] = useState(false);
  const [gmailOAuthStatus, setGmailOAuthStatus] = useState<GmailOAuthStatus>(
    EMPTY_GMAIL_OAUTH_STATUS,
  );
  const [customerForm] = Form.useForm();
  const pendingSendRef = useRef<PendingSend | null>(null);
  const pendingSendTimerRef = useRef<number | null>(null);

  const issueQuery = useMemo(() => {
    const params = new URLSearchParams({
      page: String(issues.page),
      pageSize: String(issues.pageSize),
      includeResolved: String(includeResolved),
    });
    if (issueSearch) {
      params.set("search", issueSearch);
    }
    for (const classification of issueClassification) {
      params.append("classification", classification);
    }
    if (issueStatus) {
      params.set("issueStatus", issueStatus);
    }
    return params.toString();
  }, [includeResolved, issueClassification, issueSearch, issueStatus, issues.page, issues.pageSize]);

  async function loadIssues() {
    const data = await fetchJson<IssuesResponse>(`/api/issues?${issueQuery}`);
    setIssues({
      ...EMPTY_ISSUES,
      ...data,
      items: data.items ?? [],
      summaryCounts: {
        ...EMPTY_ISSUES.summaryCounts,
        ...(data.summaryCounts ?? {}),
      },
    });
  }

  async function loadAnalytics() {
    const params = new URLSearchParams();
    if (analyticsStart) {
      params.set("start", `${analyticsStart}T00:00:00.000Z`);
    }
    if (analyticsEnd) {
      params.set("end", `${analyticsEnd}T23:59:59.999Z`);
    }
    const data = await fetchJson<AnalyticsResponse>(
      `/api/analytics${params.toString() ? `?${params.toString()}` : ""}`,
    );
    setAnalytics({
      ...EMPTY_ANALYTICS,
      ...data,
      typeCounts: data.typeCounts ?? [],
      statusCounts: data.statusCounts ?? [],
      buckets: data.buckets ?? [],
    });
  }

  async function loadGmailOAuthStatus() {
    const data = await fetchJson<GmailOAuthStatus>("/api/gmail/oauth/status");
    setGmailOAuthStatus({
      ...EMPTY_GMAIL_OAUTH_STATUS,
      ...data,
    });
  }

  async function loadReviewQueue() {
    const data = await fetchJson<CustomerResponse>("/api/customers/review?page=1&pageSize=20");
    setReviewQueue({
      ...EMPTY_CUSTOMERS,
      ...data,
      items: data.items ?? [],
    });
    setCustomerDescriptions((current) => {
      const next = { ...current };
      for (const item of data.items) {
        next[item.id] = next[item.id] ?? item.description;
      }
      return next;
    });
    return data;
  }

  async function loadCustomers(page = customers.page, pageSize = customers.pageSize) {
    const params = new URLSearchParams({
      page: String(page),
      pageSize: String(pageSize),
    });
    if (customerSearch) {
      params.set("search", customerSearch);
    }
    params.append("status", "approved");
    if (showIgnoredCustomers) {
      params.append("status", "ignored");
    }
    const data = await fetchJson<CustomerResponse>(`/api/customers?${params.toString()}`);
    setCustomers({
      ...EMPTY_CUSTOMERS,
      ...data,
      items: data.items ?? [],
    });
    return data;
  }

  async function refreshDashboard() {
    setRefreshingDashboard(true);
    try {
      await Promise.all([
        loadIssues(),
        loadAnalytics(),
        loadReviewQueue(),
        loadCustomers(),
        loadGmailOAuthStatus(),
      ]);
    } finally {
      setRefreshingDashboard(false);
    }
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      const data = await fetchJson<IssuesResponse>(`/api/issues?${issueQuery}`);
      if (!active) {
        return;
      }
      setIssues({
        ...EMPTY_ISSUES,
        ...data,
        items: data.items ?? [],
        summaryCounts: {
          ...EMPTY_ISSUES.summaryCounts,
          ...(data.summaryCounts ?? {}),
        },
      });
    })();
    return () => {
      active = false;
    };
  }, [issueQuery]);

  useEffect(() => {
    let active = true;
    void (async () => {
      const params = new URLSearchParams();
      if (analyticsStart) {
        params.set("start", `${analyticsStart}T00:00:00.000Z`);
      }
      if (analyticsEnd) {
        params.set("end", `${analyticsEnd}T23:59:59.999Z`);
      }
      const data = await fetchJson<AnalyticsResponse>(
        `/api/analytics${params.toString() ? `?${params.toString()}` : ""}`,
      );
      if (!active) {
        return;
      }
      setAnalytics({
        ...EMPTY_ANALYTICS,
        ...data,
        typeCounts: data.typeCounts ?? [],
        statusCounts: data.statusCounts ?? [],
        buckets: data.buckets ?? [],
      });
    })();
    return () => {
      active = false;
    };
  }, [analyticsStart, analyticsEnd]);

  useEffect(() => {
    let active = true;
    void (async () => {
      const data = await fetchJson<GmailOAuthStatus>("/api/gmail/oauth/status");
      if (active) {
        setGmailOAuthStatus({
          ...EMPTY_GMAIL_OAUTH_STATUS,
          ...data,
        });
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      const reviewData = await fetchJson<CustomerResponse>("/api/customers/review?page=1&pageSize=20");
      if (active) {
        setReviewQueue({
          ...EMPTY_CUSTOMERS,
          ...reviewData,
          items: reviewData.items ?? [],
        });
        setCustomerDescriptions((current) => {
          const next = { ...current };
          for (const item of reviewData.items ?? []) {
            next[item.id] = next[item.id] ?? item.description;
          }
          return next;
        });
      }

      const params = new URLSearchParams({
        page: "1",
        pageSize: String(customers.pageSize),
      });
      if (customerSearch) {
        params.set("search", customerSearch);
      }
      params.append("status", "approved");
      if (showIgnoredCustomers) {
        params.append("status", "ignored");
      }
      const customerData = await fetchJson<CustomerResponse>(`/api/customers?${params.toString()}`);
      if (!active) {
        return;
      }
      setCustomers({
        ...EMPTY_CUSTOMERS,
        ...customerData,
        items: customerData.items ?? [],
      });
    })();
    return () => {
      active = false;
    };
  }, [customerSearch, customers.pageSize, showIgnoredCustomers]);

  async function patchIssue(
    issueId: number,
    body: {
      action?:
        | "approve_to_send"
        | "mark_resolved"
        | "queue_send"
        | "send_approved"
        | "revoke_send_approval";
      draftReplyHtml?: string;
    },
  ) {
    const response = await fetchJson<PatchIssueResponse>(`/api/issues/${issueId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    await Promise.all([loadIssues(), loadReviewQueue(), loadCustomers()]);
    return response;
  }

  async function reviewCustomerAction(customerId: number, status: "approved" | "ignored") {
    await fetchJson(`/api/customers/review/${customerId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        status,
        description: customerDescriptions[customerId] ?? "",
      }),
    });
    const [reviewData] = await Promise.all([loadReviewQueue(), loadCustomers()]);
    if ((reviewData?.total ?? 0) === 0) {
      setReviewDrawerOpen(false);
    }
  }

  async function saveCustomer() {
    const values = await customerForm.validateFields();
    if (editingCustomer) {
      await fetchJson(`/api/customers/${editingCustomer.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
      });
    } else {
      await fetchJson("/api/customers", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
      });
    }
    setCustomerModalOpen(false);
    setEditingCustomer(null);
    customerForm.resetFields();
    await loadCustomers();
  }

  function openIssue(record: IssueItem) {
    setSelectedIssue(record);
    setDraftHtml(record.draftReplyHtml ?? "<p></p>");
  }

  function setIssueStatusLocally(issueId: number, issueStatus: string) {
    setSelectedIssue((current) =>
      current && current.id === issueId
        ? {
            ...current,
            issueStatus,
          }
        : current,
    );
    setIssues((current) => ({
      ...current,
      items: current.items.map((item) =>
        item.id === issueId
          ? {
              ...item,
              issueStatus,
            }
          : item,
      ),
    }));
  }

  function startEditingCustomer(record: CustomerItem) {
    setEditingCustomer(record);
    customerForm.setFieldsValue({
      email: record.email,
      displayName: record.displayName,
      description: record.description,
      status: record.status,
    });
    setCustomerModalOpen(true);
  }

  function openCustomer(record: CustomerItem) {
    setSelectedCustomer(record);
  }

  async function setCustomerStatus(record: CustomerItem, status: "approved" | "ignored") {
    await fetchJson(`/api/customers/${record.id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    });
    setSelectedCustomer((current) =>
      current && current.id === record.id
        ? {
            ...current,
            status,
          }
        : current,
    );
    await Promise.all([loadCustomers(), loadReviewQueue()]);
  }

  useEffect(() => {
    if (!pendingSend) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setPendingNow(Date.now());
    }, 250);

    return () => {
      window.clearInterval(interval);
    };
  }, [pendingSend]);

  useEffect(() => {
    return () => {
      if (pendingSendTimerRef.current) {
        window.clearTimeout(pendingSendTimerRef.current);
      }
    };
  }, []);

  function cancelPendingSend() {
    const pending = pendingSendRef.current;
    if (pendingSendTimerRef.current) {
      window.clearTimeout(pendingSendTimerRef.current);
      pendingSendTimerRef.current = null;
    }
    pendingSendRef.current = null;
    setPendingSend(null);
    if (pending) {
      setIssueStatusLocally(pending.issueId, pending.previousStatus);
    }
  }

  function queueIssueSend(record: IssueItem, nextDraftHtml: string) {
    if (pendingSendRef.current?.issueId === record.id) {
      cancelPendingSend();
      return;
    }

    cancelPendingSend();
    const scheduled: PendingSend = {
      issueId: record.id,
      label: `Reply to ${record.customerName || record.customerEmail}`,
      draftHtml: nextDraftHtml,
      mode: gmailConnectorEnabled ? "connector" : "oauth",
      expiresAt: pendingNow + ACTION_DELAY_MS,
      previousStatus: record.issueStatus,
    };
    pendingSendRef.current = scheduled;
    setPendingSend(scheduled);
    setIssueStatusLocally(record.id, "approved_to_send");
    pendingSendTimerRef.current = window.setTimeout(() => {
      pendingSendTimerRef.current = null;
      pendingSendRef.current = null;
      setPendingSend(null);
      void patchIssue(record.id, {
        draftReplyHtml: nextDraftHtml,
        action: scheduled.mode === "connector" ? "queue_send" : "send_approved",
      })
        .then((result) => {
          if (result.sent || result.manuallyResolved) {
            setSelectedIssue(null);
            return;
          }
          if (result.queued) {
            setIssueStatusLocally(record.id, "approved_to_send");
            return;
          }
          setIssueStatusLocally(record.id, "sync_error");
        })
        .catch((error: unknown) => {
          console.error("Deferred send failed", error);
          setIssueStatusLocally(record.id, "sync_error");
        });
    }, ACTION_DELAY_MS);
  }

  async function revokeIssueSendApproval(record: IssueItem) {
    await patchIssue(record.id, { action: "revoke_send_approval" });
    setIssueStatusLocally(record.id, "draft_ready");
  }

  function renderIssueSendAction(record: IssueItem) {
    if (pendingSend?.issueId === record.id) {
      return (
        <Button type="primary" onClick={() => queueIssueSend(record, draftHtml)}>
          {pendingSend.mode === "connector" ? "Cancel Approval" : "Cancel Send"}
        </Button>
      );
    }

    if (record.issueStatus === "approved_to_send") {
      return (
        <>
          <Button type="primary" disabled>
            Approved to Send
          </Button>
          <Button onClick={() => void revokeIssueSendApproval(record)}>Cancel Approval</Button>
        </>
      );
    }

    if (record.issueStatus === "resolved") {
      return <Button disabled>Resolved</Button>;
    }

    return (
      <Button type="primary" onClick={() => queueIssueSend(record, draftHtml)}>
        {gmailConnectorEnabled ? "Approve for Connector" : "Approve & Send"}
      </Button>
    );
  }

  const issueColumns = [
    {
      title: "Customer",
      dataIndex: "customerName",
      key: "customerName",
      render: (_value: string, record: IssueItem) => (
        <div>
          <div>{record.customerName || record.customerEmail}</div>
          <Text type="secondary">{record.customerEmail}</Text>
        </div>
      ),
    },
    {
      title: "Summary",
      dataIndex: "summary",
      key: "summary",
    },
    {
      title: "Type",
      dataIndex: "classification",
      key: "classification",
      render: (value: string) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: "Actions",
      key: "actions",
      width: 96,
      render: (_value: unknown, record: IssueItem) => (
        <Space size={4} wrap className="issue-action-group">
          <Tooltip title="Mark Resolved" placement="left">
            <Button
              aria-label="Mark Resolved"
              title="Mark Resolved"
              size="small"
              shape="circle"
              icon={<CheckCircleOutlined />}
              onClick={(event) => {
                event.stopPropagation();
                void patchIssue(record.id, { action: "mark_resolved" });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const reviewColumns = [
    {
      title: "Customer",
      dataIndex: "displayName",
      key: "displayName",
      render: (_value: string, record: CustomerItem) => (
        <div>
          <div>{record.displayName || record.email}</div>
          <Text type="secondary">{record.email}</Text>
        </div>
      ),
    },
    {
      title: "Description",
      key: "description",
      render: (_value: unknown, record: CustomerItem) => (
        <Input.TextArea
          value={customerDescriptions[record.id] ?? record.description}
          autoSize={{ minRows: 2, maxRows: 4 }}
          onChange={(event) =>
            setCustomerDescriptions((current) => ({
              ...current,
              [record.id]: event.target.value,
            }))
          }
        />
      ),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_value: unknown, record: CustomerItem) => (
        <Space>
          <Button size="small" type="primary" onClick={() => void reviewCustomerAction(record.id, "approved")}>
            Approve
          </Button>
          <Button size="small" danger onClick={() => void reviewCustomerAction(record.id, "ignored")}>
            Ignore
          </Button>
        </Space>
      ),
    },
  ];

  const customerColumns = [
    {
      title: "Customer",
      key: "customer",
      render: (_value: unknown, record: CustomerItem) => (
        <div>
          <Space size={6} align="center">
            <div>{record.displayName || record.email}</div>
            {record.status === "ignored" ? (
              <Tooltip title="Ignored" placement="right">
                <StopOutlined style={{ color: "#b42318" }} />
              </Tooltip>
            ) : null}
          </Space>
          <Text type="secondary">{record.email}</Text>
        </div>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
    },
    {
      title: "Issues",
      dataIndex: "issueCount",
      key: "issueCount",
    },
    {
      title: "Actions",
      key: "actions",
      width: 88,
      render: (_value: unknown, record: CustomerItem) => (
        <Space size={4} className="customer-action-group">
          <Tooltip
            title={record.status === "approved" ? "Allow customer" : "Ignore customer"}
            placement="left"
          >
            <Switch
              aria-label={record.status === "approved" ? "Allow customer" : "Ignore customer"}
              checked={record.status === "approved"}
              checkedChildren="Allow"
              unCheckedChildren="Ignore"
              onClick={(checked, event) => {
                event?.stopPropagation();
                void setCustomerStatus(record, checked ? "approved" : "ignored");
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="dashboard-shell">
      <div className="dashboard-header">
        <div>
          <Title level={2}>Customer Email Assist</Title>
          <Paragraph type="secondary">
            Minimal-token customer support triage with deterministic sync, Gmail actions, and local review.
          </Paragraph>
        </div>
        <Space wrap>
          <Card>
            <Statistic title="Total issues" value={issues.summaryCounts.total} />
          </Card>
          <Card>
            <Statistic title="Pending drafts" value={issues.summaryCounts.draft_ready} />
          </Card>
          <Card>
            <Statistic title="Approved to send" value={issues.summaryCounts.approved_to_send} />
          </Card>
        </Space>
      </div>

      <Tabs
        defaultActiveKey="issues"
        items={[
          {
            key: "issues",
            label: "Issues",
            children: (
              <Space orientation="vertical" size="large" style={{ display: "flex" }}>
                <Card>
                  <Space wrap>
                    <Input.Search
                      placeholder="Search issues"
                      value={issueSearch}
                      allowClear
                      onChange={(event) => setIssueSearch(event.target.value)}
                      style={{ width: 240 }}
                    />
                    <Select
                      mode="multiple"
                      maxTagCount="responsive"
                      allowClear
                      placeholder="Classification"
                      value={issueClassification}
                      onChange={(value) => setIssueClassification(value)}
                      style={{ width: 260 }}
                      options={[
                        { value: "query", label: "query" },
                        { value: "complaint", label: "complaint" },
                        { value: "refund_request", label: "refund_request" },
                        { value: "billing_issue", label: "billing_issue" },
                        { value: "handoff_required", label: "handoff_required" },
                      ]}
                    />
                    <Select
                      allowClear
                      placeholder="Issue status"
                      value={issueStatus}
                      onChange={setIssueStatus}
                      style={{ width: 220 }}
                      options={[
                        { value: "draft_ready", label: "draft_ready" },
                        { value: "approved_to_send", label: "approved_to_send" },
                        { value: "resolved", label: "resolved" },
                        { value: "sync_error", label: "sync_error" },
                      ]}
                    />
                    <div className="issues-filter-toggle">
                      <Text type="secondary">Show resolved</Text>
                      <Switch
                        aria-label="Show resolved"
                        checked={includeResolved}
                        onChange={setIncludeResolved}
                      />
                    </div>
                    <div className="gmail-mode-toggle" role="radiogroup" aria-label="Gmail mode">
                      <Text type="secondary">Gmail mode</Text>
                      <label
                        className={
                          gmailConnectorEnabled
                            ? "gmail-mode-option"
                            : "gmail-mode-option gmail-mode-option-active"
                        }
                        onClick={() => setGmailConnectorEnabled(false)}
                      >
                        <input
                          type="radio"
                          name="gmail-mode"
                          checked={!gmailConnectorEnabled}
                          onClick={() => setGmailConnectorEnabled(false)}
                          onChange={() => setGmailConnectorEnabled(false)}
                        />
                        <span>
                          OAuth
                        </span>
                      </label>
                      <label
                        className={
                          gmailConnectorEnabled
                            ? "gmail-mode-option gmail-mode-option-active"
                            : "gmail-mode-option"
                        }
                        onClick={() => setGmailConnectorEnabled(true)}
                      >
                        <input
                          type="radio"
                          name="gmail-mode"
                          checked={gmailConnectorEnabled}
                          onClick={() => setGmailConnectorEnabled(true)}
                          onChange={() => setGmailConnectorEnabled(true)}
                        />
                        <span>
                          Gmail connector
                        </span>
                      </label>
                    </div>
                    {!gmailConnectorEnabled ? (
                      gmailOAuthStatus.connected ? (
                        <Tooltip
                          title={
                            gmailOAuthStatus.emailAddress
                              ? `Connected as ${gmailOAuthStatus.emailAddress}`
                              : "Local OAuth is connected."
                          }
                          placement="top"
                        >
                          <Tag color="success" className="connection-mode-tag">
                            Gmail connected
                          </Tag>
                        </Tooltip>
                      ) : (
                        <Tooltip
                          title={
                            gmailOAuthStatus.configured
                              ? "Open Google consent and connect this local dashboard to Gmail."
                              : "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET before connecting Gmail."
                          }
                          placement="top"
                        >
                          <Button
                            disabled={!gmailOAuthStatus.configured}
                            onClick={() => {
                              window.location.href = "/api/gmail/oauth/start";
                            }}
                          >
                            Connect Gmail
                          </Button>
                        </Tooltip>
                      )
                    ) : null}
                    <Tooltip title="Refresh" placement="top">
                      <Button
                        aria-label="Refresh"
                        title="Refresh"
                        shape="circle"
                        icon={<ReloadOutlined />}
                        loading={refreshingDashboard}
                        onClick={() => void refreshDashboard()}
                      />
                    </Tooltip>
                  </Space>
                </Card>
                <Table
                  rowKey="id"
                  dataSource={issues.items}
                  columns={issueColumns}
                  rowClassName={() => "issue-row"}
                  onRow={(record) => ({
                    onClick: () => openIssue(record),
                  })}
                  pagination={{
                    current: issues.page,
                    pageSize: issues.pageSize,
                    total: issues.total,
                    onChange: (page, pageSize) =>
                      setIssues((current) => ({
                        ...current,
                        page,
                        pageSize,
                      })),
                  }}
                />
              </Space>
            ),
          },
          {
            key: "analysis",
            label: "Analysis",
            children: (
              <Space orientation="vertical" size="large" style={{ display: "flex" }}>
                <Card>
                  <Space wrap>
                    <Input
                      type="date"
                      value={analyticsStart}
                      onChange={(event) => setAnalyticsStart(event.target.value)}
                    />
                    <Input
                      type="date"
                      value={analyticsEnd}
                      onChange={(event) => setAnalyticsEnd(event.target.value)}
                    />
                    <Button onClick={() => void loadAnalytics()}>Refresh Analysis</Button>
                  </Space>
                </Card>
                <div className="analytics-grid">
                  <Card title="Counts by Type">
                      <Space orientation="vertical" style={{ width: "100%" }}>
                      {analytics.typeCounts.map((entry) => (
                        <div key={entry.classification} className="bar-row">
                          <Text>{entry.classification}</Text>
                          <div className="bar-track">
                            <div className="bar-fill" style={{ width: `${Math.max(entry.count, 1) * 16}px` }} />
                          </div>
                          <Text>{entry.count}</Text>
                        </div>
                      ))}
                    </Space>
                  </Card>
                  <Card title="Counts by Status">
                      <Space orientation="vertical" style={{ width: "100%" }}>
                      {analytics.statusCounts.map((entry) => (
                        <div key={entry.issueStatus} className="bar-row">
                          <Text>{entry.issueStatus}</Text>
                          <div className="bar-track">
                            <div className="bar-fill bar-fill--status" style={{ width: `${Math.max(entry.count, 1) * 16}px` }} />
                          </div>
                          <Text>{entry.count}</Text>
                        </div>
                      ))}
                    </Space>
                  </Card>
                </div>
              </Space>
            ),
          },
          {
            key: "customers",
            label: "Customers",
            children: (
              <Space orientation="vertical" size="large" style={{ display: "flex" }}>
                <Card>
                  <Space wrap>
                    <Input.Search
                      placeholder="Search customers"
                      value={customerSearch}
                      allowClear
                      onChange={(event) => setCustomerSearch(event.target.value)}
                      style={{ width: 240 }}
                    />
                    <div className="customer-filter-toggle">
                      <Text type="secondary">Show ignored</Text>
                      <Switch
                        aria-label="Show ignored"
                        checked={showIgnoredCustomers}
                        onChange={setShowIgnoredCustomers}
                      />
                    </div>
                    <Button
                      type="primary"
                      onClick={() => {
                        setEditingCustomer(null);
                        customerForm.resetFields();
                        setCustomerModalOpen(true);
                      }}
                    >
                      Add Customer
                    </Button>
                    {reviewQueue.total > 0 ? (
                      <Button onClick={() => setReviewDrawerOpen(true)}>
                        {`Customer Review (${reviewQueue.total})`}
                      </Button>
                    ) : null}
                  </Space>
                </Card>
                <Table
                  rowKey="id"
                  dataSource={customers.items}
                  columns={customerColumns}
                  rowClassName={() => "customer-row"}
                  onRow={(record) => ({
                    onClick: () => openCustomer(record),
                  })}
                  pagination={{
                    current: customers.page,
                    pageSize: customers.pageSize,
                    total: customers.total,
                    onChange: (page, pageSize) => void loadCustomers(page, pageSize),
                  }}
                />
              </Space>
            ),
          },
        ]}
      />

      <Drawer
        title={selectedIssue ? `Issue #${selectedIssue.id}` : "Issue"}
        open={Boolean(selectedIssue)}
        size="large"
        onClose={() => {
          if (pendingSend?.issueId === selectedIssue?.id) {
            cancelPendingSend();
          }
          setSelectedIssue(null);
        }}
        extra={
          selectedIssue ? (
            <Space>
              <Button onClick={() => void patchIssue(selectedIssue.id, { draftReplyHtml: draftHtml })}>Save Draft</Button>
              {renderIssueSendAction(selectedIssue)}
            </Space>
          ) : null
        }
      >
        {selectedIssue ? (
          <Space orientation="vertical" size="large" style={{ display: "flex" }}>
            {pendingSend?.issueId === selectedIssue.id ? (
              <Alert
                className="pending-action-banner"
                type="warning"
                showIcon
                title={`${pendingSend.label} approved to send`}
                description={
                  <Space wrap>
                    <Text>
                      {pendingSend.mode === "connector"
                        ? `Queuing for connector in ${Math.max(
                            1,
                            Math.ceil((pendingSend.expiresAt - pendingNow) / 1000),
                          )}s.`
                        : `Sending in ${Math.max(
                            1,
                            Math.ceil((pendingSend.expiresAt - pendingNow) / 1000),
                          )}s.`}
                    </Text>
                    <Button size="small" onClick={cancelPendingSend}>
                      Undo
                    </Button>
                  </Space>
                }
              />
            ) : null}
            {selectedIssue.issueStatus === "approved_to_send" && pendingSend?.issueId !== selectedIssue.id ? (
              <Alert
                className="pending-action-banner"
                type="info"
                showIcon
                title="Approved to send"
                description="This issue is already approved for the next selected send runner. It cannot be approved again; cancel approval if you need to return it to draft review."
              />
            ) : null}
            <Card size="small" title="Issue Summary">
              <div className={`issue-summary-panel issue-summary-panel--${selectedIssue.urgency}`}>
                <Text strong className="issue-summary-text">
                  {selectedIssue.summary}
                </Text>
                <Space wrap size={[8, 8]} className="issue-summary-meta">
                  <Tag color={toClassificationColor(selectedIssue.classification)}>
                    Type: {selectedIssue.classification}
                  </Tag>
                  <Tag color={toUrgencyColor(selectedIssue.urgency)}>
                    Urgency: {selectedIssue.urgency}
                  </Tag>
                  <Tag color={toActionSuggestionColor(selectedIssue.actionSuggestion)}>
                    Action: {selectedIssue.actionSuggestion}
                  </Tag>
                  <Tag color={toStatusColor(selectedIssue.issueStatus)}>
                    Status: {selectedIssue.issueStatus}
                  </Tag>
                </Space>
              </div>
            </Card>
            <Card size="small" title="Original Message">
              <Paragraph>{selectedIssue.originalMessageText ?? "No message body stored."}</Paragraph>
            </Card>
            <Card size="small" title="Policy Evidence">
              <Space orientation="vertical" style={{ display: "flex" }}>
                {(selectedIssue.policyEvidence ?? []).map((entry) => (
                  <Text key={entry}>{entry}</Text>
                ))}
                {(selectedIssue.policyEvidence ?? []).length === 0 ? (
                  <Text type="secondary">No stored policy evidence yet.</Text>
                ) : null}
              </Space>
            </Card>
            <Card size="small" title="Draft Reply">
              <RichTextEditor value={draftHtml} onChange={setDraftHtml} />
            </Card>
          </Space>
        ) : null}
      </Drawer>

      <Drawer
        title={`Customer Review (${reviewQueue.total})`}
        open={reviewDrawerOpen}
        size="large"
        onClose={() => setReviewDrawerOpen(false)}
      >
        <Table
          rowKey="id"
          dataSource={reviewQueue.items}
          columns={reviewColumns}
          pagination={{
            current: reviewQueue.page,
            pageSize: reviewQueue.pageSize,
            total: reviewQueue.total,
          }}
        />
      </Drawer>

      <Drawer
        title={selectedCustomer ? selectedCustomer.displayName || selectedCustomer.email : "Customer"}
        open={Boolean(selectedCustomer)}
        size="default"
        onClose={() => setSelectedCustomer(null)}
        extra={
          selectedCustomer ? (
            <Button
              onClick={() => {
                startEditingCustomer(selectedCustomer);
                setSelectedCustomer(null);
              }}
            >
              Edit Customer
            </Button>
          ) : null
        }
      >
        {selectedCustomer ? (
          <Space orientation="vertical" size="large" style={{ display: "flex" }}>
            <Card size="small" title="Customer Summary">
              <Space orientation="vertical" style={{ display: "flex" }}>
                <div>
                  <Text strong>Email</Text>
                  <Paragraph copyable={{ text: selectedCustomer.email }}>{selectedCustomer.email}</Paragraph>
                </div>
                <Space wrap>
                  <Tag color={toStatusColor(selectedCustomer.status)}>{selectedCustomer.status}</Tag>
                  <Tag color="blue">{`${selectedCustomer.issueCount} issue${selectedCustomer.issueCount === 1 ? "" : "s"}`}</Tag>
                </Space>
                <div>
                  <Text strong>Last seen</Text>
                  <Paragraph>{selectedCustomer.lastSeenAt ?? "No activity recorded yet."}</Paragraph>
                </div>
              </Space>
            </Card>
            <Card size="small" title="Description">
              <Paragraph>{selectedCustomer.description || "No description yet."}</Paragraph>
            </Card>
          </Space>
        ) : null}
      </Drawer>

      <Modal
        title={editingCustomer ? "Edit Customer" : "Add Customer"}
        open={customerModalOpen}
        onCancel={() => {
          setCustomerModalOpen(false);
          setEditingCustomer(null);
        }}
        onOk={() => void saveCustomer()}
      >
        <Form
          form={customerForm}
          layout="vertical"
          initialValues={{
            status: "approved",
          }}
        >
          <Form.Item label="Email" name="email" rules={[{ required: true, type: "email" }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Display name" name="displayName" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Description" name="description">
            <Input.TextArea autoSize={{ minRows: 3, maxRows: 5 }} />
          </Form.Item>
          <Form.Item label="Status" name="status" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "pending", label: "pending" },
                { value: "approved", label: "approved" },
                { value: "ignored", label: "ignored" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
