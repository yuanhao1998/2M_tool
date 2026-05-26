import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Account } from '@/types'

interface Props {
  open: boolean
  onClose: () => void
  onSave: (data: Partial<Account>) => void
  account?: Account | null
}

const fields: { key: string; label: string; required?: boolean }[] = [
  { key: 'account_name', label: '账号名', required: true },
  { key: 'phone', label: '手机号', required: true },
  { key: 'cloud_device', label: '云机名称', required: true },
  { key: 'email', label: '邮箱' },
  { key: 'server', label: '区服' },
  { key: 'region', label: '大区' },
  { key: 'class', label: '职业' },
  { key: 'pin_code', label: 'PIN 码' },
  { key: 'location', label: '地点' },
  { key: 'verify_code_url', label: '验证码 URL' },
  { key: 'recovery_code', label: '修复码' },
]

export default function AccountForm({ open, onClose, onSave, account }: Props) {
  const [form, setForm] = useState<Record<string, string>>({})

  useEffect(() => {
    if (account) {
      const data: Record<string, string> = {}
      for (const f of fields) {
        data[f.key] = (account as any)[f.key] || ''
      }
      setForm(data)
    } else {
      setForm(Object.fromEntries(fields.map((f) => [f.key, ''])))
    }
  }, [account, open])

  const handleSubmit = async () => {
    if (!account) {
      for (const f of fields) {
        if (f.required && !form[f.key]?.trim()) {
          alert(`${f.label} 不能为空`)
          return
        }
      }
    }
    try {
      await onSave({ ...form })
      onClose()
    } catch (err: any) {
      alert(err.message || '保存失败')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{account ? '编辑账号' : '新增账号'}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          {fields.map((f) => (
            <div key={f.key} className="space-y-1">
              <Label>{f.label}{f.required && <span className="text-red-500 ml-0.5">*</span>}</Label>
              <Input
                value={form[f.key] || ''}
                onChange={(e) => setForm((s) => ({ ...s, [f.key]: e.target.value }))}
              />
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button onClick={handleSubmit}>保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
