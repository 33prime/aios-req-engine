'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { X, Check, ChevronRight, Plus, Trash2 } from 'lucide-react'
import { CreationAnimation } from './CreationAnimation'
import { createProjectWithContext } from '@/lib/api'

type CreationStep = 'name' | 'problem' | 'beneficiaries' | 'features' | 'company' | 'creating' | 'complete'

interface ProjectData {
  name: string
  problem: string
  beneficiaries: string
  features: string[]
  companyName: string
  companyWebsite: string
}

interface GuidedProjectCreationProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (response: any) => void
}

const REQUIRED_STEPS: CreationStep[] = ['name', 'problem', 'beneficiaries', 'features']
const MIN_FEATURES = 2
const MAX_FEATURES = 4

export function GuidedProjectCreation({ isOpen, onClose, onSuccess }: GuidedProjectCreationProps) {
  const [step, setStep] = useState<CreationStep>('name')
  const [data, setData] = useState<ProjectData>({
    name: '',
    problem: '',
    beneficiaries: '',
    features: ['', ''],
    companyName: '',
    companyWebsite: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [showCompanyInputs, setShowCompanyInputs] = useState<boolean | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [createdProject, setCreatedProject] = useState<any>(null)

  const inputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-focus on step change
  useEffect(() => {
    if (!isOpen) return
    const timer = setTimeout(() => {
      if (step === 'name' || step === 'features') {
        inputRef.current?.focus()
      } else if (step === 'problem' || step === 'beneficiaries') {
        textareaRef.current?.focus()
      }
    }, 100)
    return () => clearTimeout(timer)
  }, [step, isOpen])

  // Reset on close
  useEffect(() => {
    if (!isOpen) {
      setStep('name')
      setData({
        name: '',
        problem: '',
        beneficiaries: '',
        features: ['', ''],
        companyName: '',
        companyWebsite: '',
      })
      setError(null)
      setShowCompanyInputs(null)
      setIsSubmitting(false)
      setCreatedProject(null)
    }
  }, [isOpen])

  const getStepNumber = () => {
    const stepIndex = REQUIRED_STEPS.indexOf(step as any)
    return stepIndex >= 0 ? stepIndex + 1 : REQUIRED_STEPS.length
  }

  const isStepComplete = (checkStep: CreationStep): boolean => {
    switch (checkStep) {
      case 'name':
        return data.name.trim().length >= 3
      case 'problem':
        return data.problem.trim().length >= 20
      case 'beneficiaries':
        return data.beneficiaries.trim().length >= 10
      case 'features':
        return data.features.filter((f) => f.trim().length > 0).length >= MIN_FEATURES
      default:
        return false
    }
  }

  const validateCurrentStep = (): string | null => {
    switch (step) {
      case 'name':
        if (data.name.trim().length < 3) return 'Project name must be at least 3 characters'
        return null
      case 'problem':
        if (data.problem.trim().length < 20) return 'Please provide more detail about the problem (at least 20 characters)'
        return null
      case 'beneficiaries':
        if (data.beneficiaries.trim().length < 10) return 'Please describe who benefits from this solution'
        return null
      case 'features':
        const validFeatures = data.features.filter((f) => f.trim().length > 0)
        if (validFeatures.length < MIN_FEATURES) return `Please add at least ${MIN_FEATURES} features`
        return null
      default:
        return null
    }
  }

  const goToNextStep = () => {
    const validationError = validateCurrentStep()
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)

    switch (step) {
      case 'name':
        setStep('problem')
        break
      case 'problem':
        setStep('beneficiaries')
        break
      case 'beneficiaries':
        setStep('features')
        break
      case 'features':
        setStep('company')
        break
      case 'company':
        handleSubmit()
        break
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      goToNextStep()
    }
  }

  const handleTextareaKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      goToNextStep()
    }
    // Shift+Enter allows new line (default behavior)
  }

  const addFeature = () => {
    if (data.features.length < MAX_FEATURES) {
      setData((prev) => ({ ...prev, features: [...prev.features, ''] }))
    }
  }

  const removeFeature = (index: number) => {
    if (data.features.length > MIN_FEATURES) {
      setData((prev) => ({
        ...prev,
        features: prev.features.filter((_, i) => i !== index),
      }))
    }
  }

  const updateFeature = (index: number, value: string) => {
    setData((prev) => ({
      ...prev,
      features: prev.features.map((f, i) => (i === index ? value : f)),
    }))
  }

  const handleCompanyChoice = (hasCompany: boolean) => {
    setShowCompanyInputs(hasCompany)
    if (!hasCompany) {
      handleSubmit()
    }
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setStep('creating')

    try {
      const payload = {
        name: data.name.trim(),
        problem: data.problem.trim(),
        beneficiaries: data.beneficiaries.trim(),
        features: data.features.filter((f) => f.trim().length > 0),
        company_name: data.companyName.trim() || undefined,
        company_website: data.companyWebsite.trim() || undefined,
      }

      const response = await createProjectWithContext(payload)
      setCreatedProject(response)
    } catch (err: any) {
      console.error('Failed to create project:', err)
      setError(err.message || 'Failed to create project')
      setStep('company')
      setIsSubmitting(false)
    }
  }

  const handleAnimationComplete = () => {
    if (createdProject) {
      onSuccess(createdProject)
    }
  }

  const handleClose = () => {
    // Warn if data entered
    const hasData = data.name || data.problem || data.beneficiaries || data.features.some((f) => f)
    if (hasData && step !== 'creating') {
      if (!window.confirm('You have unsaved changes. Are you sure you want to close?')) {
        return
      }
    }
    onClose()
  }

  if (!isOpen) return null

  // Show animation during creation
  if (step === 'creating') {
    return <CreationAnimation projectName={data.name} onComplete={handleAnimationComplete} />
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">New Project</h2>
            {step !== 'company' && (
              <p className="text-sm text-gray-500">Step {getStepNumber()} of {REQUIRED_STEPS.length}</p>
            )}
          </div>

          {/* Progress dots */}
          <div className="flex items-center gap-4">
            <div className="flex gap-1.5">
              {REQUIRED_STEPS.map((s, i) => (
                <div
                  key={s}
                  className={`w-2.5 h-2.5 rounded-full transition-colors ${
                    i < getStepNumber() - 1
                      ? 'bg-[#009b87]'
                      : i === getStepNumber() - 1 && step !== 'company'
                      ? 'bg-[#009b87]'
                      : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
            <button
              onClick={handleClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Completed steps summary */}
          <div className="space-y-3 mb-6">
            {/* Name */}
            {(step !== 'name' && data.name) && (
              <div className="flex items-start gap-2 text-sm">
                <Check className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-gray-500">Project Name:</span>
                  <span className="ml-2 text-gray-900 font-medium">{data.name}</span>
                </div>
              </div>
            )}

            {/* Problem */}
            {(['beneficiaries', 'features', 'company'].includes(step) && data.problem) && (
              <div className="flex items-start gap-2 text-sm">
                <Check className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-gray-500">Problem:</span>
                  <span className="ml-2 text-gray-700 line-clamp-2">{data.problem}</span>
                </div>
              </div>
            )}

            {/* Beneficiaries */}
            {(['features', 'company'].includes(step) && data.beneficiaries) && (
              <div className="flex items-start gap-2 text-sm">
                <Check className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-gray-500">Who Benefits:</span>
                  <span className="ml-2 text-gray-700 line-clamp-2">{data.beneficiaries}</span>
                </div>
              </div>
            )}

            {/* Features */}
            {(step === 'company' && data.features.filter(f => f).length > 0) && (
              <div className="flex items-start gap-2 text-sm">
                <Check className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-gray-500">Features:</span>
                  <span className="ml-2 text-gray-700">
                    {data.features.filter(f => f).join(', ')}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Current step input */}
          <div className="space-y-4">
            {/* Step: Name */}
            {step === 'name' && (
              <div>
                <label className="flex items-center gap-2 text-gray-900 font-medium mb-3">
                  <ChevronRight className="w-4 h-4 text-[#009b87]" />
                  What should we call this project?
                </label>
                <input
                  ref={inputRef}
                  type="text"
                  value={data.name}
                  onChange={(e) => setData((prev) => ({ ...prev, name: e.target.value }))}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g., Customer Portal Redesign"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
                  autoFocus
                />
                <p className="text-sm text-gray-400 mt-2">
                  Something descriptive that identifies the project
                </p>
              </div>
            )}

            {/* Step: Problem */}
            {step === 'problem' && (
              <div>
                <label className="flex items-center gap-2 text-gray-900 font-medium mb-3">
                  <ChevronRight className="w-4 h-4 text-[#009b87]" />
                  What problem does this solve?
                </label>
                <textarea
                  ref={textareaRef}
                  value={data.problem}
                  onChange={(e) => setData((prev) => ({ ...prev, problem: e.target.value }))}
                  onKeyDown={handleTextareaKeyDown}
                  placeholder="Describe the main challenge or pain point this project addresses..."
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent resize-none"
                />
                <p className="text-sm text-gray-400 mt-2">
                  What pain point or challenge are you addressing?
                </p>
              </div>
            )}

            {/* Step: Beneficiaries */}
            {step === 'beneficiaries' && (
              <div>
                <label className="flex items-center gap-2 text-gray-900 font-medium mb-3">
                  <ChevronRight className="w-4 h-4 text-[#009b87]" />
                  Who benefits from this solution?
                </label>
                <textarea
                  ref={textareaRef}
                  value={data.beneficiaries}
                  onChange={(e) => setData((prev) => ({ ...prev, beneficiaries: e.target.value }))}
                  onKeyDown={handleTextareaKeyDown}
                  placeholder="Describe the target users or personas who will use this..."
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent resize-none"
                />
                <p className="text-sm text-gray-400 mt-2">
                  Who are the primary users that will benefit?
                </p>
              </div>
            )}

            {/* Step: Features */}
            {step === 'features' && (
              <div>
                <label className="flex items-center gap-2 text-gray-900 font-medium mb-3">
                  <ChevronRight className="w-4 h-4 text-[#009b87]" />
                  What are the core features? ({MIN_FEATURES}-{MAX_FEATURES} required)
                </label>
                <div className="space-y-3">
                  {data.features.map((feature, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="text-sm text-gray-500 w-6">{index + 1}.</span>
                      <input
                        ref={index === 0 ? inputRef : undefined}
                        type="text"
                        value={feature}
                        onChange={(e) => updateFeature(index, e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={`Feature ${index + 1}`}
                        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
                      />
                      {data.features.length > MIN_FEATURES && (
                        <button
                          onClick={() => removeFeature(index)}
                          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                {data.features.length < MAX_FEATURES && (
                  <button
                    onClick={addFeature}
                    className="mt-3 flex items-center gap-2 text-sm text-[#009b87] hover:text-[#007a6b] font-medium"
                  >
                    <Plus className="w-4 h-4" />
                    Add another feature
                  </button>
                )}
                <p className="text-sm text-gray-400 mt-3">
                  Keep it high-level, e.g., &ldquo;Real-time order tracking&rdquo;
                </p>
              </div>
            )}

            {/* Step: Company */}
            {step === 'company' && showCompanyInputs === null && (
              <div>
                <label className="flex items-center gap-2 text-gray-900 font-medium mb-4">
                  <ChevronRight className="w-4 h-4 text-[#009b87]" />
                  Do you have company information to add?
                </label>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleCompanyChoice(true)}
                    className="flex-1 px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 hover:border-[#009b87] transition-colors"
                  >
                    Yes, add company info
                  </button>
                  <button
                    onClick={() => handleCompanyChoice(false)}
                    className="flex-1 px-4 py-3 bg-[#009b87] text-white rounded-lg font-medium hover:bg-[#007a6b] transition-colors"
                  >
                    Skip for now
                  </button>
                </div>
              </div>
            )}

            {/* Company inputs shown */}
            {step === 'company' && showCompanyInputs === true && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Company Name
                  </label>
                  <input
                    ref={inputRef}
                    type="text"
                    value={data.companyName}
                    onChange={(e) => setData((prev) => ({ ...prev, companyName: e.target.value }))}
                    onKeyDown={handleKeyDown}
                    placeholder="e.g., Acme Corporation"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Website (optional)
                  </label>
                  <input
                    type="url"
                    value={data.companyWebsite}
                    onChange={(e) => setData((prev) => ({ ...prev, companyWebsite: e.target.value }))}
                    onKeyDown={handleKeyDown}
                    placeholder="e.g., https://acme.com"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Error display */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Press <kbd className="px-1.5 py-0.5 bg-gray-200 rounded text-xs font-mono">Enter</kbd> to continue
          </p>
          <button
            onClick={goToNextStep}
            disabled={isSubmitting}
            className="px-6 py-2.5 bg-[#009b87] text-white rounded-lg font-medium hover:bg-[#007a6b] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {step === 'company' && showCompanyInputs === true ? (
              <>Create Project</>
            ) : step === 'features' ? (
              <>Continue</>
            ) : (
              <>Next</>
            )}
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
