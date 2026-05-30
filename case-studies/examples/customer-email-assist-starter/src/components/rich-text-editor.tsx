"use client";

import { useEffect } from "react";

import { Button, Space } from "antd";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export function RichTextEditor({ value, onChange }: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [StarterKit],
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

  return (
    <div className="rich-text-editor">
      <Space wrap>
        <Button
          size="small"
          type={editor.isActive("bold") ? "primary" : "default"}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          Bold
        </Button>
        <Button
          size="small"
          type={editor.isActive("italic") ? "primary" : "default"}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          Italic
        </Button>
        <Button
          size="small"
          type={editor.isActive("bulletList") ? "primary" : "default"}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          Bullets
        </Button>
      </Space>
      <EditorContent editor={editor} />
    </div>
  );
}
