import { Editor, EditorProps } from "@monaco-editor/react";
import { cn } from "@/lib/utils";

interface Props extends EditorProps {
  className?: string;
}

export default function CodeEditor({ className, ...props }: Props) {
  return (
    <div className={cn("border rounded overflow-hidden shadow-sm flex flex-col h-full bg-[#1e1e1e]", className)}>
      <Editor
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          wordWrap: "on",
          padding: { top: 16, bottom: 16 },
          scrollBeyondLastLine: false,
          smoothScrolling: true,
          cursorBlinking: "smooth",
          renderLineHighlight: "all",
          ...props.options
        }}
        {...props}
      />
    </div>
  );
}
