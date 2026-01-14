# AIOS Design System & UI Guide

The authoritative reference for all frontend development. Follow these patterns exactly.

---

## Table of Contents

1. [Colors](#colors)
2. [Typography](#typography)
3. [Icons](#icons)
4. [Buttons](#buttons)
5. [Badges & Pills](#badges--pills)
6. [Form Elements](#form-elements)
7. [Cards](#cards)
8. [Tab Navigation](#tab-navigation)
9. [Accordions](#accordions)
10. [Modals](#modals)
11. [Side Panels](#side-panels)
12. [Progress Indicators](#progress-indicators)
13. [Empty States](#empty-states)
14. [Page Layouts](#page-layouts)
15. [Auth Screens](#auth-screens)

---

## Colors

### Primary

| Name          | Hex     | Usage                      |
|---------------|---------|----------------------------|
| Teal          | #009b87 | Primary buttons, CTAs, active states |
| Teal Hover    | #007a6b | Hover states               |
| Icon Gray     | #778191 | Default icon color         |

### Status

| State   | Background    | Text           |
|---------|---------------|----------------|
| Success | bg-green-100  | text-green-800 |
| Warning | bg-yellow-100 | text-yellow-800|
| Error   | bg-red-100    | text-red-800   |
| Info    | bg-blue-50    | text-blue-700  |

### Grays

```
gray-50:  #FAFAFA  (page backgrounds)
gray-100: #F5F5F5  (disabled states)
gray-200: #E5E5E5  (borders, dividers)
gray-300: #D4D4D4  (input borders)
gray-400: #A3A3A3  (placeholder, subtle icons)
gray-500: #737373  (secondary text)
gray-600: #525252  (body text)
gray-700: #404040  (emphasis text)
gray-900: #171717  (headings, primary text)
```

### Accents

| Name        | Hex     | Usage                    |
|-------------|---------|--------------------------|
| Emerald 50  | #ecfdf5 | Light backgrounds        |
| Emerald 100 | #d1fae5 | Badges, avatar backgrounds |
| Emerald 700 | #047857 | Accent text              |

---

## Typography

**Font:** `'Inter', system-ui, sans-serif`

| Element          | Classes                                              |
|------------------|------------------------------------------------------|
| Page Title       | `text-3xl font-bold text-gray-900`                   |
| Section Title    | `text-xl font-semibold text-gray-900`                |
| Card Title       | `text-lg font-semibold text-gray-900`                |
| Accordion Title  | `text-base font-semibold text-[#009b87]`             |
| Section Header   | `text-xs font-semibold text-[#009b87] uppercase tracking-wide` |
| Body Text        | `text-sm text-gray-700` or `text-sm text-[#374151]`  |
| Metadata         | `text-sm text-gray-600`                              |
| Small Text       | `text-xs text-gray-500`                              |
| Placeholder      | `text-gray-500 italic`                               |

---

## Icons

**Library:** Lucide React

### Sizing

| Size   | Class        | Usage                    |
|--------|--------------|--------------------------|
| XS     | `w-3 h-3`    | Inside badges, inline    |
| SM     | `w-4 h-4`    | Buttons, metadata, cards |
| MD     | `w-5 h-5`    | Navigation, headers      |
| LG     | `w-6 h-6`    | Modal close, prominent   |
| XL     | `w-8 h-8`    | Empty state icons        |
| Hero   | `w-12 h-12`  | Empty state hero         |

### Colors

| Context        | Class                |
|----------------|----------------------|
| Default        | `text-[#778191]`     |
| Interactive    | `hover:text-[#009b87]` |
| Active/Accent  | `text-[#009b87]`     |
| Muted          | `text-gray-400`      |

### Common Icons

- **Navigation:** ArrowLeft, X, ChevronRight
- **Actions:** Plus, Edit, Upload, Download, Mail, Search
- **Content:** FileText, Calendar, Clock, Users, Target
- **Status:** CheckCircle, AlertCircle, Loader

---

## Buttons

### Primary

```jsx
<button className="px-4 py-2 bg-[#009b87] text-white rounded-lg hover:bg-[#007a6b] transition-colors">
  Submit
</button>
```

### Primary (Full Width, Auth)

```jsx
<button className="w-full bg-gradient-to-br from-emerald-600 to-emerald-400 text-white py-2 rounded-lg text-sm font-medium hover:from-emerald-700 hover:to-emerald-500 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed">
  Log in
</button>
```

### Secondary/Outline

```jsx
<button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
  Cancel
</button>
```

### Ghost (Selectable/Toggle)

```jsx
<button className={`flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-[#009b87] hover:text-[#009b87] transition-colors ${
  isSelected ? 'border-[#009b87] text-[#009b87] bg-gray-50' : ''
}`}>
  <Icon className="w-4 h-4" />
  Label
</button>
```

### Icon Button (Card Actions)

```jsx
<button className="p-2 text-[#778191] hover:text-[#009b87] hover:bg-gray-50 rounded-lg transition-colors" title="Action">
  <Icon className="w-4 h-4" />
</button>
```

### Small Link

```jsx
<button className="text-xs text-[#009b87] hover:underline flex items-center gap-1">
  <Plus className="w-3 h-3" />
  Add Item
</button>
```

### Disabled State

Add `disabled:opacity-50 disabled:cursor-not-allowed` to any button.

### Loading State

```jsx
<button disabled={loading}>
  {loading ? (
    <div className="flex items-center justify-center">
      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
      Loading...
    </div>
  ) : 'Submit'}
</button>
```

---

## Badges & Pills

### Type Badge (Contextual Colors)

```jsx
const getTypeColor = (type: string) => {
  switch (type) {
    case 'Intro': return 'bg-emerald-50 text-[#009b87]';
    case 'Discovery': return 'bg-emerald-100 text-[#007a6b]';
    case 'Prototype Review': return 'bg-[#009b87] text-white';
    case 'Proposal': return 'bg-[#007a6b] text-white';
    default: return 'bg-gray-100 text-gray-800';
  }
};

<span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${getTypeColor(type)}`}>
  {type}
</span>
```

### Status Badge

```jsx
<span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
  Published
</span>
```

### Removable Tag/Pill

```jsx
<span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-100 text-emerald-700 text-xs rounded-full">
  <Mail className="w-3 h-3" />
  {label}
  <button onClick={onRemove} className="ml-1 hover:text-red-600">
    <X className="w-3 h-3" />
  </button>
</span>
```

### Numbered Circle

```jsx
<div className="h-6 w-6 md:h-7 md:w-7 rounded-full bg-[#009b87] flex items-center justify-center text-xs font-semibold text-white">
  {number}
</div>
```

### Avatar/Initials

```jsx
<div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-xs font-medium text-emerald-700">
  {initials}
</div>
```

---

## Form Elements

### Text Input

```jsx
<input
  type="text"
  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
  placeholder="Enter text"
/>
```

### Input with Icon

```jsx
<div className="relative">
  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
  <input
    type="text"
    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#009b87]"
    placeholder="Search..."
  />
</div>
```

### Underline Input

```jsx
<input
  type="text"
  className="w-full pb-2 border-b border-gray-300 focus:border-[#009b87] focus:outline-none text-sm"
/>
```

### Textarea

```jsx
<textarea
  rows={6}
  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent text-sm text-gray-700 resize-none"
  placeholder="Enter content..."
/>
```

### Label

```jsx
<label className="block text-sm font-medium text-gray-700 mb-1">
  Field Label
</label>
```

### Checkbox

```jsx
<div className="flex items-center">
  <input
    type="checkbox"
    className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 border-gray-300 rounded"
  />
  <label className="ml-2 block text-sm text-gray-700">Label</label>
</div>
```

### File Upload Zone

```jsx
<div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-[#009b87] transition-colors">
  {file ? (
    <div className="space-y-2">
      <div className="w-12 h-12 bg-[#009b87] rounded-full flex items-center justify-center mx-auto">
        <FileText className="w-6 h-6 text-white" />
      </div>
      <p className="text-sm font-medium text-gray-900">{file.name}</p>
      <p className="text-xs text-gray-500">{fileSize} MB</p>
    </div>
  ) : (
    <div className="space-y-2">
      <Upload className="w-12 h-12 text-gray-400 mx-auto" />
      <p className="text-sm text-gray-600">Click to select or drag and drop</p>
      <p className="text-xs text-gray-500">PDF, DOC, DOCX up to 10MB</p>
    </div>
  )}
</div>
```

---

## Cards

### Standard Card

```jsx
<div className="bg-white rounded-xl border border-gray-200 p-4 md:p-5">
  <div className="flex items-center justify-between mb-3">
    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
      <Icon className="w-4 h-4 mr-2 text-[#778191]" />
      Card Title
    </h3>
    <div className="flex items-center space-x-2">
      {/* Action icons */}
    </div>
  </div>
  <div className="text-gray-700 leading-relaxed">
    {/* Content */}
  </div>
</div>
```

### Info Box (Blue)

```jsx
<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
  <h4 className="text-sm font-medium text-blue-900 mb-2">Title</h4>
  <div className="text-xs text-blue-700 space-y-1">
    <div>• Point one</div>
    <div>• Point two</div>
  </div>
</div>
```

---

## Tab Navigation

```jsx
<div className="border-b border-gray-200">
  <nav className="-mb-px flex space-x-8">
    {tabs.map((tab) => (
      <button
        key={tab.id}
        onClick={() => setActiveTab(tab.id)}
        className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
          activeTab === tab.id
            ? 'border-[#009b87] text-[#009b87]'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }`}
      >
        <tab.icon className="w-4 h-4 mr-2 text-[#778191]" />
        {tab.label}
      </button>
    ))}
  </nav>
</div>
```

---

## Accordions

### Container

```jsx
<div className="border border-gray-200 rounded-lg overflow-hidden">
```

### Header

```jsx
<button
  onClick={toggle}
  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors duration-200"
>
  <div className="flex-1">
    <div className="flex items-baseline gap-2 mb-1">
      <div className="h-6 w-6 rounded-full bg-[#009b87] flex items-center justify-center text-xs font-semibold text-white">
        {number}
      </div>
      <h4 className="text-base font-semibold text-[#009b87]">{title}</h4>
    </div>
    <div className="flex items-center gap-1 ml-8">
      <Clock className="w-3 h-3 text-[#778191]" />
      <span className="text-xs text-gray-500">{duration}</span>
    </div>
  </div>
  <ChevronRight className={`w-4 h-4 text-[#778191] transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`} />
</button>
```

### Content

```jsx
<div className={`transition-all duration-200 ${isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0 overflow-hidden'}`}>
  <div className="px-4 pb-4 border-t border-gray-100">
    <div className="pt-4 space-y-4">
      <h5 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide mb-2">Section</h5>
      <ul className="text-sm text-[#374151] space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex items-start">
            <span className="text-[#009b87] mr-2">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  </div>
</div>
```

---

## Modals

### Overlay

```jsx
<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
```

### Container

```jsx
<div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
```

### Header

```jsx
<div className="flex items-center justify-between p-6 border-b border-gray-200">
  <h2 className="text-lg font-semibold text-gray-900">Title</h2>
  <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
    <X className="w-6 h-6" />
  </button>
</div>
```

### Content

```jsx
<div className="p-6 space-y-4 overflow-y-auto">
  {/* Content */}
</div>
```

### Footer

```jsx
<div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
  <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
    Cancel
  </button>
  <button className="px-4 py-2 bg-[#009b87] text-white rounded-lg hover:bg-[#007a6b] transition-colors">
    Submit
  </button>
</div>
```

### Size Variants

| Type     | Width      |
|----------|------------|
| Small    | max-w-md   |
| Standard | max-w-2xl  |
| Large    | max-w-4xl  |

---

## Side Panels

```jsx
{/* Backdrop */}
<div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={onClose} />

{/* Panel */}
<div className="fixed top-0 right-0 h-full w-[32%] bg-white shadow-xl z-50 transform transition-transform duration-300 ease-in-out">
  {/* Header */}
  <div className="flex items-center justify-between p-6 border-b border-gray-200">
    <h2 className="text-xl font-semibold text-gray-900 flex items-center">
      <Icon className="w-5 h-5 mr-2 text-[#778191]" />
      Panel Title
    </h2>
    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
      <X className="w-6 h-6" />
    </button>
  </div>

  {/* Content */}
  <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(100vh-120px)]">
    {/* Content */}
  </div>
</div>
```

---

## Progress Indicators

### Linear Bar

```jsx
<div className="w-full bg-gray-200 rounded-full h-2">
  <div
    className="bg-[#009b87] h-2 rounded-full transition-all duration-300"
    style={{ width: `${percent}%` }}
  />
</div>
```

### With Label

```jsx
<div className="space-y-2">
  <div className="flex items-center justify-between text-sm">
    <span className="text-gray-600">Uploading...</span>
    <span className="text-gray-600">{percent}%</span>
  </div>
  <div className="w-full bg-gray-200 rounded-full h-2">
    <div className="bg-[#009b87] h-2 rounded-full transition-all duration-300" style={{ width: `${percent}%` }} />
  </div>
</div>
```

---

## Empty States

### Simple

```jsx
<p className="text-gray-500 italic text-center py-4">No items available</p>
```

### With Icon

```jsx
<div className="text-center py-12">
  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
    <FileText className="w-8 h-8 text-gray-400" />
  </div>
  <h3 className="text-lg font-semibold text-gray-900 mb-2">No Content</h3>
  <p className="text-gray-600 text-sm max-w-md mx-auto">
    Description of what to do next.
  </p>
</div>
```

---

## Page Layouts

### Detail Page

```jsx
<div className="min-h-screen bg-gray-50 p-8">
  {/* Back Navigation */}
  <button className="flex items-center text-gray-600 hover:text-gray-900 transition-colors duration-200 mb-6">
    <ArrowLeft className="w-5 h-5 mr-2" />
    Back to List
  </button>

  {/* Title + Badge */}
  <div className="mb-6">
    <div className="flex items-baseline space-x-3 mb-2">
      <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
      <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${badgeColor}`}>
        {type}
      </span>
    </div>
    <p className="text-base text-gray-600 mt-2">{description}</p>
  </div>

  {/* Metadata Row */}
  <div className="flex items-center space-x-3 text-sm text-gray-600 mb-8">
    <span className="flex items-center">
      <Calendar className="w-4 h-4 mr-1" />
      {date}
    </span>
    <span className="text-gray-300">•</span>
    <span className="flex items-center">
      <Clock className="w-4 h-4 mr-1" />
      {duration}
    </span>
  </div>

  {/* Tabs */}
  {/* Tab Content */}
</div>
```

---

## Auth Screens

### Split Layout

```jsx
<div className="min-h-screen flex">
  {/* Left Hero (hidden mobile) */}
  <div className="hidden md:flex w-1/2 bg-gradient-to-br from-emerald-600 to-emerald-400 rounded-r-3xl flex-col justify-center items-center p-12 text-white relative">
    <div className="absolute top-6 left-6">
      <img src="/logo.svg" alt="Logo" className="h-8" />
    </div>
    <h1 className="text-5xl font-semibold mb-6 text-center max-w-lg">
      Your headline here
    </h1>
    <p className="text-lg max-w-md text-center">Subtext</p>
  </div>

  {/* Right Form */}
  <div className="flex-1 flex items-center justify-center bg-zinc-50">
    <div className="max-w-md bg-white rounded-xl shadow-sm border border-zinc-200 p-8 w-full mx-4">
      {/* Form content */}
    </div>
  </div>
</div>
```

### Error Alert

```jsx
<div className="flex items-center p-4 rounded-lg mb-6 bg-red-50 border border-red-200">
  <AlertCircle className="w-5 h-5 mr-3 text-red-600" />
  <p className="text-sm text-red-700">{error}</p>
</div>
```

### Divider

```jsx
<div className="flex items-center my-4">
  <div className="flex-1 h-px bg-zinc-200" />
  <span className="px-3 text-xs text-zinc-500">or</span>
  <div className="flex-1 h-px bg-zinc-200" />
</div>
```

### Footer Link

```jsx
<p className="text-sm text-zinc-600 text-center mt-6">
  Don't have an account?{' '}
  <button className="text-[#009b87] font-medium hover:underline">Sign up</button>
</p>
```

---

## Transitions

Default: `transition-colors` (150ms)

For transforms/all: `transition-all duration-200 ease-in-out`

For panels: `transition-transform duration-300 ease-in-out`
