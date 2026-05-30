"use client";

import { useEffect } from "react";

import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import TaskItem from "@tiptap/extension-task-item";
import TaskList from "@tiptap/extension-task-list";
import TextAlign from "@tiptap/extension-text-align";
import Underline from "@tiptap/extension-underline";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Button, Segmented, Select, Space, Tooltip, Typography } from "antd";
import {
  AlignCenterOutlined,
  AlignLeftOutlined,
  AlignRightOutlined,
  BgColorsOutlined,
  BoldOutlined,
  CheckSquareOutlined,
  DisconnectOutlined,
  ItalicOutlined,
  LinkOutlined,
  OrderedListOutlined,
  RedoOutlined,
  StrikethroughOutlined,
  UndoOutlined,
  UnderlineOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
}

const blockOptions = [
  { label: "Paragraph", value: "paragraph" },
  { label: "Heading 1", value: "heading-1" },
  { label: "Heading 2", value: "heading-2" },
  { label: "Heading 3", value: "heading-3" },
];

function getBlockValue(editor: ReturnType<typeof useEditor>) {
  if (!editor) {
    return "paragraph";
  }
  if (editor.isActive("heading", { level: 1 })) {
    return "heading-1";
  }
  if (editor.isActive("heading", { level: 2 })) {
    return "heading-2";
  }
  if (editor.isActive("heading", { level: 3 })) {
    return "heading-3";
  }
  return "paragraph";
}

export function RichTextEditor({ value, onChange }: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
        link: false,
        underline: false,
      }),
      Underline,
      Link.configure({
        autolink: true,
        defaultProtocol: "https",
        openOnClick: false,
      }),
      Placeholder.configure({
        placeholder: "Draft the customer reply here...",
      }),
      TextAlign.configure({
        types: ["heading", "paragraph"],
      }),
      TaskList,
      TaskItem.configure({
        nested: true,
      }),
    ],
    content: value,
    immediatelyRender: false,
    onUpdate: ({ editor: activeEditor }) => {
      onChange(activeEditor.getHTML());
    },
    editorProps: {
      attributes: {
        class: "rich-text-editor__content",
      },
    },
  });

  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value, { emitUpdate: false });
    }
  }, [editor, value]);

  if (!editor) {
    return null;
  }

  const activeEditor = editor;
  const blockValue = getBlockValue(activeEditor);
  const alignmentValue = activeEditor.isActive({ textAlign: "center" })
    ? "center"
    : activeEditor.isActive({ textAlign: "right" })
      ? "right"
      : "left";

  function setBlockType(next: string) {
    if (next === "paragraph") {
      activeEditor.chain().focus().setParagraph().run();
      return;
    }

    const headingLevelMap = {
      "heading-1": 1,
      "heading-2": 2,
      "heading-3": 3,
    } as const;

    const level = headingLevelMap[next as keyof typeof headingLevelMap];
    if (level) {
      activeEditor.chain().focus().setHeading({ level }).run();
    }
  }

  function setLink() {
    const previous = activeEditor.getAttributes("link").href as string | undefined;
    const input = window.prompt("Enter a link URL", previous ?? "");
    if (input === null) {
      return;
    }

    const next = input.trim();
    if (!next) {
      activeEditor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }

    const normalized = /^(https?:\/\/|mailto:)/i.test(next) ? next : `https://${next}`;
    activeEditor.chain().focus().extendMarkRange("link").setLink({ href: normalized }).run();
  }

  return (
    <div className="rich-text-editor">
      <div className="rich-text-editor__toolbar">
        <div className="rich-text-editor__toolbar-group">
          <Text type="secondary" className="rich-text-editor__toolbar-label">
            Block
          </Text>
          <Select
            aria-label="Block type"
            size="small"
            value={blockValue}
            onChange={setBlockType}
            options={blockOptions}
            style={{ width: 138 }}
          />
        </div>
        <span aria-hidden className="rich-text-editor__divider" />
        <Space.Compact size="small" className="rich-text-editor__toolbar-group">
          <Tooltip title="Bold">
            <Button
              size="small"
              type={activeEditor.isActive("bold") ? "primary" : "default"}
              icon={<BoldOutlined />}
              onClick={() => activeEditor.chain().focus().toggleBold().run()}
            />
          </Tooltip>
          <Tooltip title="Italic">
            <Button
              size="small"
              type={activeEditor.isActive("italic") ? "primary" : "default"}
              icon={<ItalicOutlined />}
              onClick={() => activeEditor.chain().focus().toggleItalic().run()}
            />
          </Tooltip>
          <Tooltip title="Underline">
            <Button
              size="small"
              type={activeEditor.isActive("underline") ? "primary" : "default"}
              icon={<UnderlineOutlined />}
              onClick={() => activeEditor.chain().focus().toggleUnderline().run()}
            />
          </Tooltip>
          <Tooltip title="Strike">
            <Button
              size="small"
              type={activeEditor.isActive("strike") ? "primary" : "default"}
              icon={<StrikethroughOutlined />}
              onClick={() => activeEditor.chain().focus().toggleStrike().run()}
            />
          </Tooltip>
        </Space.Compact>
        <span aria-hidden className="rich-text-editor__divider" />
        <Space.Compact size="small" className="rich-text-editor__toolbar-group">
          <Tooltip title="Bulleted list">
            <Button
              size="small"
              type={activeEditor.isActive("bulletList") ? "primary" : "default"}
              icon={<UnorderedListOutlined />}
              onClick={() => activeEditor.chain().focus().toggleBulletList().run()}
            />
          </Tooltip>
          <Tooltip title="Numbered list">
            <Button
              size="small"
              type={activeEditor.isActive("orderedList") ? "primary" : "default"}
              icon={<OrderedListOutlined />}
              onClick={() => activeEditor.chain().focus().toggleOrderedList().run()}
            />
          </Tooltip>
          <Tooltip title="Checklist">
            <Button
              size="small"
              type={activeEditor.isActive("taskList") ? "primary" : "default"}
              icon={<CheckSquareOutlined />}
              onClick={() => activeEditor.chain().focus().toggleTaskList().run()}
            />
          </Tooltip>
          <Tooltip title="Quote">
            <Button
              size="small"
              type={activeEditor.isActive("blockquote") ? "primary" : "default"}
              icon={<BgColorsOutlined />}
              onClick={() => activeEditor.chain().focus().toggleBlockquote().run()}
            />
          </Tooltip>
        </Space.Compact>
        <span aria-hidden className="rich-text-editor__divider" />
        <div className="rich-text-editor__toolbar-group">
          <Text type="secondary" className="rich-text-editor__toolbar-label">
            Align
          </Text>
          <Segmented
            size="small"
            value={alignmentValue}
            onChange={(next) => activeEditor.chain().focus().setTextAlign(String(next)).run()}
            options={[
              { value: "left", icon: <AlignLeftOutlined /> },
              { value: "center", icon: <AlignCenterOutlined /> },
              { value: "right", icon: <AlignRightOutlined /> },
            ]}
          />
        </div>
        <span aria-hidden className="rich-text-editor__divider" />
        <Space.Compact size="small" className="rich-text-editor__toolbar-group">
          <Tooltip title="Add or edit link">
            <Button
              size="small"
              type={activeEditor.isActive("link") ? "primary" : "default"}
              icon={<LinkOutlined />}
              onClick={setLink}
            />
          </Tooltip>
          <Tooltip title="Remove link">
            <Button
              size="small"
              icon={<DisconnectOutlined />}
              disabled={!activeEditor.isActive("link")}
              onClick={() =>
                activeEditor.chain().focus().extendMarkRange("link").unsetLink().run()
              }
            />
          </Tooltip>
        </Space.Compact>
        <div className="rich-text-editor__toolbar-spacer" />
        <Space.Compact size="small" className="rich-text-editor__toolbar-group">
          <Tooltip title="Undo">
            <Button
              size="small"
              icon={<UndoOutlined />}
              disabled={!activeEditor.can().chain().focus().undo().run()}
              onClick={() => activeEditor.chain().focus().undo().run()}
            />
          </Tooltip>
          <Tooltip title="Redo">
            <Button
              size="small"
              icon={<RedoOutlined />}
              disabled={!activeEditor.can().chain().focus().redo().run()}
              onClick={() => activeEditor.chain().focus().redo().run()}
            />
          </Tooltip>
        </Space.Compact>
      </div>
      <div className="rich-text-editor__surface">
        <EditorContent editor={activeEditor} />
      </div>
      <div className="rich-text-editor__footer">
        <Text type="secondary">
          Draft with headings, lists, checklists, quotes, links, alignment, and undo or redo support.
        </Text>
      </div>
    </div>
  );
}
