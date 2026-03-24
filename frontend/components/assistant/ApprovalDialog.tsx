"use client"

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ShieldAlert, CheckCircle, XCircle } from "lucide-react"

interface ApprovalDialogProps {
  open: boolean
  agent: any
  onApprove: () => void
  onReject: () => void
}

export function ApprovalDialog({ open, agent, onApprove, onReject }: ApprovalDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onReject() }}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-amber-500">
            <ShieldAlert className="h-5 w-5" />
            Human-in-the-Loop Required
          </DialogTitle>
          <DialogDescription>
            High-Risk operation requested by Cortex Swarm.
          </DialogDescription>
        </DialogHeader>
        
        <div className="py-4 space-y-4">
          <div className="bg-muted p-3 rounded-md text-sm">
            <p><strong>Agent:</strong> {agent?.name}</p>
            <p><strong>Role:</strong> {agent?.type}</p>
            <p className="mt-2 text-muted-foreground">
              This workflow executes critical operations that require explicit human approval due to current compliance settings.
            </p>
          </div>
        </div>

        <DialogFooter className="flex space-x-2 justify-end">
          <Button variant="outline" onClick={onReject} className="flex items-center gap-2">
            <XCircle className="h-4 w-4" />
            Reject
          </Button>
          <Button onClick={onApprove} className="bg-amber-600 hover:bg-amber-700 text-white flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            Approve Execution
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}