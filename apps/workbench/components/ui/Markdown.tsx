/**
 * Markdown Component
 *
 * Renders markdown content with proper styling.
 * Supports GitHub Flavored Markdown (tables, task lists, strikethrough, etc.)
 */

'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownProps {
  content: string
  className?: string
}

export function Markdown({ content, className = '' }: MarkdownProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
        // Headings - smaller for chat context
        h1: ({ node, ...props }) => <h1 className="text-base font-bold mt-3 mb-1.5" {...props} />,
        h2: ({ node, ...props }) => <h2 className="text-sm font-bold mt-2 mb-1" {...props} />,
        h3: ({ node, ...props }) => <h3 className="text-sm font-semibold mt-2 mb-1" {...props} />,

        // Paragraphs
        p: ({ node, ...props }) => <p className="mb-1.5 last:mb-0" {...props} />,

        // Lists - tighter spacing
        ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-1.5 space-y-0.5" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-1.5 space-y-0.5" {...props} />,
        li: ({ node, ...props }) => <li className="ml-2" {...props} />,

        // Code
        code: ({ node, inline, ...props }: any) =>
          inline ? (
            <code className="bg-gray-100 text-red-600 px-1 py-0.5 rounded text-xs font-mono" {...props} />
          ) : (
            <code className="block bg-gray-100 text-gray-800 p-2.5 rounded text-xs font-mono overflow-x-auto mb-1.5" {...props} />
          ),
        pre: ({ node, ...props }) => <pre className="mb-1.5" {...props} />,

        // Links
        a: ({ node, ...props }) => (
          <a
            className="text-[#3FAF7A] hover:text-[#25785A] underline"
            target="_blank"
            rel="noopener noreferrer"
            {...props}
          />
        ),

        // Blockquotes
        blockquote: ({ node, ...props }) => (
          <blockquote className="border-l-2 border-gray-300 pl-3 italic my-1.5 text-gray-600" {...props} />
        ),

        // Tables - lighter styling for chat
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto mb-1.5">
            <table className="min-w-full border-collapse text-sm" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => <thead {...props} />,
        th: ({ node, ...props }) => <th className="border-b border-gray-200 px-2 py-1.5 text-left font-medium bg-gray-50" {...props} />,
        td: ({ node, ...props }) => <td className="border-b border-gray-100 px-2 py-1.5" {...props} />,

        // Horizontal rule
        hr: ({ node, ...props }) => <hr className="my-3 border-gray-200" {...props} />,

        // Strong/Em
        strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
        em: ({ node, ...props }) => <em className="italic" {...props} />,
      }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
