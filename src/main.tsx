import * as React from "react"
import { createRoot } from "react-dom/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { Calendar } from "@/components/ui/calendar"
import "./index.css"

function App() {
  const [count, setCount] = React.useState(0)
  return (
    <main className="mx-auto max-w-4xl space-y-6 p-8">
      <h1 className="text-3xl font-semibold">离线 UI 模板</h1>
      <p className="text-muted-foreground">依赖已随仓库保存。安装和构建均无需访问 npm。</p>
      <Card>
        <CardHeader><CardTitle>交互示例</CardTitle></CardHeader>
        <CardContent className="flex gap-4">
          <Button onClick={() => setCount(count + 1)}>计数：{count}</Button>
          <Dialog>
            <DialogTrigger asChild><Button variant="outline">打开对话框</Button></DialogTrigger>
            <DialogContent><DialogHeader><DialogTitle>本地构建成功</DialogTitle></DialogHeader><p>这个对话框由随仓库保存的组件构建。</p></DialogContent>
          </Dialog>
        </CardContent>
      </Card>
      <ResizablePanelGroup orientation="horizontal" className="min-h-36 rounded-md border">
        <ResizablePanel defaultSize="50%"><div className="p-6">可调整面板</div></ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize="50%"><div className="p-6">全部 npm 子包固定在 lockfile。</div></ResizablePanel>
      </ResizablePanelGroup>
      <Calendar mode="single" />
    </main>
  )
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>)
