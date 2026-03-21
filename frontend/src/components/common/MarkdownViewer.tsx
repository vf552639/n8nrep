import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
  className?: string;
}

export default function MarkdownViewer({ content, className = "" }: Props) {
  return (
    <div className={`prose prose-slate max-w-none ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content || "*No content provided*"}
      </ReactMarkdown>
    </div>
  );
}
