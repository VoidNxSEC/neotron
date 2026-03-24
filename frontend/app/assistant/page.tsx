"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Network,
  Bot,
  Play,
  Pause,
  Square,
  ArrowLeft,
  Brain,
  Zap,
  Shield,
  Code2,
  FileText,
  Settings,
  Activity,
  Clock,
  CheckCircle,
  AlertCircle,
  Users,
} from "lucide-react"
import Link from "next/link"
import { ApprovalDialog } from "@/components/assistant/ApprovalDialog"

export default function AgentOrchestra() {
  const [selectedWorkflow, setSelectedWorkflow] = useState("compliance-audit")
  const [workflowStatus, setWorkflowStatus] = useState("idle")
  const [activeAgents, setActiveAgents] = useState<any[]>([])
  const [workflowProgress, setWorkflowProgress] = useState(0)
  const [customTask, setCustomTask] = useState("")
  const [executionResult, setExecutionResult] = useState<any>(null)
  
  // Approval dialog state
  const [showApprovalDialog, setShowApprovalDialog] = useState(false)
  const [pendingAgent, setPendingAgent] = useState<any>(null)
  const [approvalResolve, setApprovalResolve] = useState<((value: boolean) => void) | null>(null)

  const workflows = [
    {
      id: "compliance-audit",
      name: "Regulatory Compliance Audit",
      description: "Multi-agent analysis using CORTEX Swarm to verify LGPD/GDPR requirements",
      agents: ["compliance_analyst", "risk_assessor", "decision_maker"],
      estimatedTime: "2-4 minutes",
      complexity: "High",
    },
    {
      id: "credit-scoring",
      name: "DeFi Credit Scoring",
      description: "Evaluate user collateral and history for Lending Protocol approval",
      agents: ["risk_assessor", "decision_maker"],
      estimatedTime: "1-2 minutes",
      complexity: "Medium",
    },
  ]

  const agents = [
    {
      id: "compliance_analyst",
      name: "Compliance Analyst",
      type: "Legal",
      status: "idle",
      llm: "Llama.cpp",
      specialization: "LGPD/GDPR/AI Act checks",
      efficiency: 98,
      tasksCompleted: 145,
    },
    {
      id: "risk_assessor",
      name: "Risk Assessor",
      type: "Risk",
      status: "idle",
      llm: "Anthropic",
      specialization: "Financial & Security Risk",
      efficiency: 95,
      tasksCompleted: 212,
    },
    {
      id: "decision_maker",
      name: "Decision Maker",
      type: "Executive",
      status: "idle",
      llm: "OpenAI",
      specialization: "Consensus Synthesis",
      efficiency: 92,
      tasksCompleted: 189,
    }
  ]

  const executeWorkflow = async () => {
    setWorkflowStatus("running")
    setWorkflowProgress(20)
    setExecutionResult(null)

    const selectedWorkflowData = workflows.find((w) => w.id === selectedWorkflow)
    const workflowAgents = agents.filter((agent) =>
      selectedWorkflowData?.agents.some((agentId) => agent.id === agentId),
    )

    setActiveAgents(workflowAgents.map((agent) => ({ ...agent, status: "active" })))

    // SIMULATE HUMAN-IN-THE-LOOP FOR HIGH RISK
    if (selectedWorkflowData?.complexity === "High") {
      setWorkflowProgress(40)
      const approved = await requestApproval(workflowAgents[0])
      if (!approved) {
        setWorkflowStatus("stopped")
        setActiveAgents((prev) => prev.map((a) => ({ ...a, status: "stopped" })))
        return
      }
    }

    try {
      const response = await fetch("http://localhost:8000/v1/test/cortex", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer DEV_TOKEN" 
        },
        body: JSON.stringify({
          agent_ids: selectedWorkflowData?.agents,
          task: "Execute " + selectedWorkflowData?.name,
          data: { context: customTask || "Standard workflow execution" },
          consensus_strategy: "weighted"
        })
      });

      setWorkflowProgress(80)

      if (!response.ok) {
        throw new Error("API Execution Failed")
      }

      const data = await response.json()
      setExecutionResult(data)
      setWorkflowProgress(100)
      
      setActiveAgents((prev) =>
        prev.map((a) => ({ ...a, status: "completed" }))
      )
      setWorkflowStatus("completed")

    } catch (error) {
      console.error(`Error executing workflow:`, error)
      setActiveAgents((prev) =>
        prev.map((a) => ({ ...a, status: "failed" }))
      )
      setWorkflowStatus("stopped")
    }
  }

  const requestApproval = (agent: any): Promise<boolean> => {
    return new Promise((resolve) => {
      setPendingAgent(agent)
      setApprovalResolve(() => resolve)
      setShowApprovalDialog(true)
    })
  }

  const handleApprove = () => {
    setShowApprovalDialog(false)
    if (approvalResolve) approvalResolve(true)
  }

  const handleReject = () => {
    setShowApprovalDialog(false)
    if (approvalResolve) approvalResolve(false)
  }

  const stopWorkflow = () => {
    setWorkflowStatus("stopped")
    setActiveAgents(activeAgents.map((agent) => ({ ...agent, status: "stopped" })))
  }

  return (
    <div className="min-h-screen bg-background pt-8 pb-16">
      <div className="container mx-auto px-4">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link href="/">
            <Button variant="outline" size="sm" className="hover:bg-muted">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Hub
            </Button>
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Network className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-foreground">NEXUS Cortex Assistant</h1>
              <p className="text-muted-foreground">Coordinate multiple AI agents for compliance and workflows</p>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Workflow Control */}
          <div className="lg:col-span-2">
            <Tabs defaultValue="workflows" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="workflows">
                  Workflows
                </TabsTrigger>
                <TabsTrigger value="execution">
                  Execution Panel
                </TabsTrigger>
                <TabsTrigger value="custom">
                  Custom Task
                </TabsTrigger>
              </TabsList>

              <TabsContent value="workflows" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Settings className="w-5 h-5 text-muted-foreground" />
                      Predefined Workflows
                    </CardTitle>
                    <CardDescription>
                      Select a workflow to orchestrate multiple AI agents
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Select value={selectedWorkflow} onValueChange={setSelectedWorkflow}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {workflows.map((workflow) => (
                          <SelectItem key={workflow.id} value={workflow.id}>
                            {workflow.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {workflows
                      .filter((w) => w.id === selectedWorkflow)
                      .map((workflow) => (
                        <div key={workflow.id} className="p-4 bg-muted/50 rounded-lg border border-border">
                          <div className="flex items-start justify-between mb-3">
                            <div>
                              <h3 className="font-medium text-foreground">{workflow.name}</h3>
                              <p className="text-muted-foreground text-sm mt-1">{workflow.description}</p>
                            </div>
                            <Badge
                              variant={
                                workflow.complexity === "Low"
                                  ? "secondary"
                                  : workflow.complexity === "Medium"
                                    ? "default"
                                    : "destructive"
                              }
                            >
                              {workflow.complexity}
                            </Badge>
                          </div>

                          <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                              <span className="text-muted-foreground text-sm">Estimated Time:</span>
                              <div className="font-medium">{workflow.estimatedTime}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground text-sm">Agents Required:</span>
                              <div className="font-medium">{workflow.agents.length}</div>
                            </div>
                          </div>

                          <div>
                            <span className="text-muted-foreground text-sm mb-2 block">Agents in Workflow:</span>
                            <div className="flex flex-wrap gap-2">
                              {workflow.agents.map((agentName) => (
                                <Badge key={agentName} variant="outline" className="bg-background">
                                  <Bot className="w-3 h-3 mr-1 text-primary" />
                                  {agentName}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                      ))}

                    <div className="flex gap-2">
                      <Button onClick={executeWorkflow} disabled={workflowStatus === "running"} className="flex-1">
                        {workflowStatus === "running" ? (
                          <>
                            <Pause className="w-4 h-4 mr-2" />
                            Running...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 mr-2" />
                            Execute Swarm Workflow
                          </>
                        )}
                      </Button>
                      {workflowStatus === "running" && (
                        <Button variant="destructive" onClick={stopWorkflow}>
                          <Square className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="execution" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="w-5 h-5 text-muted-foreground" />
                      Swarm Execution Panel
                    </CardTitle>
                    <CardDescription>
                      Real-time workflow progress and agent coordination
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Progress Bar */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-sm">Consensus Progress</span>
                        <span className="text-muted-foreground text-sm">{Math.round(workflowProgress)}%</span>
                      </div>
                      <div className="h-3 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-500"
                          style={{ width: `${workflowProgress}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Active Agents */}
                    {activeAgents.length > 0 && (
                      <div>
                        <h4 className="font-medium mb-3 text-sm">Active Swarm Agents</h4>
                        <div className="space-y-2">
                          {activeAgents.map((agent: any) => (
                            <div key={agent.id} className="flex items-center gap-3 p-3 bg-muted/50 border rounded-lg">
                              <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                                <Bot className="w-4 h-4 text-primary" />
                              </div>
                              <div className="flex-1">
                                <div className="font-medium text-sm">{agent.name}</div>
                                <div className="text-muted-foreground text-xs">{agent.specialization}</div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs bg-background">
                                  {agent.llm}
                                </Badge>
                                <div
                                  className={`w-2 h-2 rounded-full ${agent.status === "active"
                                    ? "bg-green-500 animate-pulse"
                                    : agent.status === "completed"
                                      ? "bg-blue-500"
                                      : agent.status === "stopped"
                                        ? "bg-red-500"
                                        : "bg-gray-500"
                                    }`}
                                ></div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Results Box with Typewriter Effect simulation via CSS or just clean rendering */}
                    {executionResult && (
                      <div className="mt-4 p-4 bg-muted/30 border border-border rounded-lg animate-in fade-in slide-in-from-bottom-2 duration-500">
                        <h4 className="font-bold mb-2 flex items-center gap-2 text-primary">
                          <CheckCircle className="w-5 h-5"/>
                          Consensus Reached
                        </h4>
                        <p className="text-muted-foreground text-sm italic mb-4">
                          Strategy used: {executionResult.consensus.strategy || "Weighted"}
                        </p>
                        <div className="bg-background border p-4 rounded-md text-sm whitespace-pre-wrap font-mono shadow-inner">
                          {JSON.stringify(executionResult.consensus.decision, null, 2)}
                        </div>
                        
                        <h4 className="font-semibold mt-6 mb-3 text-sm flex items-center gap-2">
                          <Users className="w-4 h-4" />
                          Individual Agent Votes:
                        </h4>
                        <div className="space-y-3">
                          {executionResult.individual_results?.map((res: any, idx: number) => (
                            <div key={idx} className="bg-background border p-3 rounded-md text-xs">
                              <div className="flex justify-between items-center mb-1">
                                <strong className="text-primary">{res.agent}</strong>
                                <Badge variant="secondary">Confidence: {res.confidence?.toFixed(2)}</Badge>
                              </div>
                              <span className="text-muted-foreground block mt-2">{JSON.stringify(res.content)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="custom" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Brain className="w-5 h-5 text-muted-foreground" />
                      Custom Swarm Task
                    </CardTitle>
                    <CardDescription>
                      Provide an arbitrary payload for the Swarm to analyze
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Textarea
                      value={customTask}
                      onChange={(e) => setCustomTask(e.target.value)}
                      placeholder="Enter task details..."
                      className="min-h-32"
                    />
                    <Button onClick={executeWorkflow} disabled={!customTask.trim()} className="w-full">
                      <Zap className="w-4 h-4 mr-2" />
                      Broadcast to Swarm
                    </Button>
                  </CardContent>
                </Card>
              </TabsContent>

            </Tabs>
          </div>

          {/* Agent Status Sidebar */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-muted-foreground" />
                  Available Agents
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {agents.map((agent) => (
                    <div key={agent.id} className="p-3 bg-muted/50 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Bot className="w-4 h-4 text-primary" />
                          <span className="font-medium text-sm">{agent.name}</span>
                        </div>
                        <div className="w-2 h-2 bg-green-500 rounded-full shadow-[0_0_8px_#22c55e]"></div>
                      </div>
                      <div className="space-y-1 text-xs">
                        <div className="flex justify-between text-muted-foreground">
                          <span>Role:</span>
                          <span className="font-medium">{agent.type}</span>
                        </div>
                        <div className="flex justify-between text-muted-foreground">
                          <span>LLM Provider:</span>
                          <span className="font-medium">{agent.llm}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-muted-foreground" />
                  Compliance Guardrails
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-2 border rounded bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
                    <div className="flex items-center text-sm text-green-700 dark:text-green-400 font-medium">
                      <CheckCircle className="w-4 h-4 mr-2" />
                      BASTION Kernel
                    </div>
                    <Badge variant="outline" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100 border-none">Active</Badge>
                  </div>
                  <div className="flex items-center justify-between p-2 border rounded bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
                    <div className="flex items-center text-sm text-green-700 dark:text-green-400 font-medium">
                      <CheckCircle className="w-4 h-4 mr-2" />
                      SENTINEL
                    </div>
                    <Badge variant="outline" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100 border-none">Active</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Approval Dialog */}
      {pendingAgent && (
        <ApprovalDialog
          open={showApprovalDialog}
          agent={pendingAgent}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}
    </div>
  )
}
