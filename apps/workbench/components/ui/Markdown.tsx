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
        // Headings
        h1: ({ node, ...props }) => <h1 className="text-xl font-bold mt-4 mb-2" {...props} />,
        h2: ({ node, ...props }) => <h2 className="text-lg font-bold mt-3 mb-2" {...props} />,
        h3: ({ node, ...props }) => <h3 className="text-base font-bold mt-2 mb-1" {...props} />,

        // Paragraphs
        p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,

        // Lists
        ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-2 space-y-1" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />,
        li: ({ node, ...props }) => <li className="ml-2" {...props} />,

        // Code
        code: ({ node, inline, ...props }: any) =>
          inline ? (
            <code className="bg-gray-100 text-red-600 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
          ) : (
            <code className="block bg-gray-900 text-gray-100 p-3 rounded text-sm font-mono overflow-x-auto mb-2" {...props} />
          ),
        pre: ({ node, ...props }) => <pre className="mb-2" {...props} />,

        // Links
        a: ({ node, ...props }) => (
          <a
            className="text-brand-primary hover:text-brand-primaryHover underline"
            target="_blank"
            rel="noopener noreferrer"
            {...props}
          />
        ),

        // Blockquotes
        blockquote: ({ node, ...props }) => (
          <blockquote className="border-l-4 border-gray-300 pl-4 italic my-2 text-gray-600" {...props} />
        ),

        // Tables
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto mb-2">
            <table className="min-w-full border border-gray-300" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => <thead className="bg-gray-100" {...props} />,
        th: ({ node, ...props }) => <th className="border border-gray-300 px-3 py-2 text-left font-semibold" {...props} />,
        td: ({ node, ...props }) => <td className="border border-gray-300 px-3 py-2" {...props} />,

        // Horizontal rule
        hr: ({ node, ...props }) => <hr className="my-4 border-gray-300" {...props} />,

        // Strong/Em
        strong: ({ node, ...props }) => <strong className="font-bold" {...props} />,
        em: ({ node, ...props }) => <em className="italic" {...props} />,
      }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
