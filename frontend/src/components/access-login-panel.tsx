"use client";

/** 共享登录弹窗：复用数据后台入口视觉，验证主站账号并按需限制超级管理员身份。 */

import { FormEvent, useState } from "react";
import { CircleAlert, ShieldCheck } from "lucide-react";

import { apiFetch, type CurrentUser, type UserRole } from "@/lib/api";

type AccessLoginPanelProps = {
  audience: "site" | "admin";
  requiredRole?: UserRole;
  onLoggedIn: (user: CurrentUser) => void;
};

  /** 提交统一登录接口；受限后台会立即撤销误登的普通用户会话。 */
export function AccessLoginPanel({ audience, requiredRole, onLoggedIn }: AccessLoginPanelProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await apiFetch<CurrentUser>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      if (requiredRole && user.role !== requiredRole) {
        await apiFetch<void>("/auth/logout", { method: "POST" });
        throw new Error("当前账号没有超级管理员权限");
      }
      onLoggedIn(user);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "登录失败，请重试");
    } finally {
      setSubmitting(false);
    }
  }

  const isAdmin = audience === "admin";
  return (
    <main className="admin-login-page">
      <form className="admin-login-card" onSubmit={submitLogin}>
        <div className="admin-kicker"><ShieldCheck size={16} />{isAdmin ? "内部数据审核" : "公司内部访问"}</div>
        <h1>{isAdmin ? "目标单位数据库" : "全国销售网络作战地图"}</h1>
        <p>{isAdmin ? "第一阶段仅超级管理员可维护业务数据和账号覆盖范围。" : "此系统仅供公司内部授权人员使用，请先登录。"}</p>
        <label>账号<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required autoFocus /></label>
        <label>密码<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required /></label>
        {error ? <p className="admin-form-error" role="alert"><CircleAlert size={15} />{error}</p> : null}
        <button className="admin-primary" disabled={submitting}>{submitting ? "正在验证…" : isAdmin ? "进入管理后台" : "进入网站"}</button>
      </form>
    </main>
  );
}
