"use client";

/** 授权账号工作台：超级管理员新增、编辑和删除普通用户及其四级覆盖范围。 */

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { CircleAlert, KeyRound, Pencil, Plus, ShieldCheck, Trash2, UserRound } from "lucide-react";

import {
  apiFetch,
  type AccountCoverageScope,
  type AuthorizedUser,
  type SalesCoverageLevel,
} from "@/lib/api";
import {
  canonicalSalesProvince,
  salesCoverageLevels,
  salesProvinces,
  salesRegionDescription,
  salesRegions,
} from "@/lib/sales-coverage";

type ScopeDraft = {
  key: string;
  scopeLevel: SalesCoverageLevel;
  scopeName: string;
  province: string;
  city: string;
  amapAdcode: string;
};

type SalespersonOption = {
  value: string;
  label: string;
};

/** 区域账号必须关联一个销售人员，全国账号无需关联即可查看全部销售。 */
function requiresLinkedSalesperson(scopes: ScopeDraft[]): boolean {
  return !scopes.some((scope) => scope.scopeLevel === "全国");
}

/** 生成仅供 React 列表使用的稳定草稿键。 */
function draftKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

/** 新范围默认从省级开始，减少普通销售账号的必填项。 */
function emptyScope(): ScopeDraft {
  return { key: draftKey(), scopeLevel: "省", scopeName: "", province: "", city: "", amapAdcode: "" };
}

/** 把 API 范围转换为不共享引用的可编辑草稿。 */
function scopeDraft(scope: AccountCoverageScope): ScopeDraft {
  return {
    key: draftKey(),
    scopeLevel: scope.scope_level,
    scopeName: scope.scope_name,
    province: canonicalSalesProvince(scope.province),
    city: scope.city ?? "",
    amapAdcode: scope.amap_adcode ?? "",
  };
}

/** 清除切换层级后不再适用的省市字段。 */
function changeScopeLevel(scopeLevel: SalesCoverageLevel): Partial<ScopeDraft> {
  return { scopeLevel, scopeName: scopeLevel === "全国" ? "全国" : "", province: "", city: "", amapAdcode: "" };
}

/** 把表单草稿裁剪为后端账号范围输入。 */
function scopePayload(scopes: ScopeDraft[]) {
  return scopes.map((scope) => ({
    scope_level: scope.scopeLevel,
    scope_name: scope.scopeName.trim(),
    province: scope.province.trim() || null,
    city: scope.city.trim() || null,
    amap_adcode: scope.amapAdcode.trim() || null,
  }));
}

/** 将服务端时间按中国地区格式展示，空值明确表示从未登录。 */
function formatAccountTime(value: string | null): string {
  return value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "从未登录";
}

/** 在账号新增和修改表单中复用同一套四级范围控件。 */
function AccountScopeEditor({ scopes, onChange }: { scopes: ScopeDraft[]; onChange: (scopes: ScopeDraft[]) => void }) {
  function update(index: number, changes: Partial<ScopeDraft>) {
    onChange(scopes.map((scope, itemIndex) => itemIndex === index ? { ...scope, ...changes } : scope));
  }

  return <div className="account-scope-editor">
    <div className="account-scope-editor-head"><strong>覆盖范围 *</strong><button type="button" onClick={() => onChange([...scopes, emptyScope()])}><Plus size={14} />添加范围</button></div>
    {scopes.length === 0 ? <p>至少添加一个市、省、大区或全国范围。</p> : null}
    {scopes.map((scope, index) => <fieldset key={scope.key}>
      <legend>范围 {index + 1}</legend>
      <button className="account-scope-remove" type="button" onClick={() => onChange(scopes.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={13} />移除</button>
      <label>层级<select aria-label={`账号覆盖层级 ${index + 1}`} value={scope.scopeLevel} onChange={(event) => update(index, changeScopeLevel(event.target.value as SalesCoverageLevel))}>{salesCoverageLevels.map((level) => <option key={level}>{level}</option>)}</select></label>
      {scope.scopeLevel === "大区" ? <label>大区<select value={scope.scopeName} onChange={(event) => update(index, { scopeName: event.target.value })} required><option value="">请选择大区</option>{salesRegions.map((region) => <option key={region}>{region}</option>)}</select><small>{scope.scopeName ? `包含：${salesRegionDescription(scope.scopeName)}` : "选择后自动包含对应省份"}</small></label> : null}
      {scope.scopeLevel === "省" ? <label>省份<select value={scope.province} onChange={(event) => update(index, { province: event.target.value, scopeName: event.target.value })} required><option value="">请选择省份</option>{salesProvinces.map((province) => <option key={province}>{province}</option>)}</select></label> : null}
      {scope.scopeLevel === "市" ? <><label>省份<select value={scope.province} onChange={(event) => update(index, { province: event.target.value })} required><option value="">请选择省份</option>{salesProvinces.map((province) => <option key={province}>{province}</option>)}</select></label><label>城市<input value={scope.city} onChange={(event) => update(index, { city: event.target.value, scopeName: event.target.value })} maxLength={60} required /></label><label>高德行政区编码<input value={scope.amapAdcode} onChange={(event) => update(index, { amapAdcode: event.target.value })} pattern="[0-9]{6}" maxLength={6} inputMode="numeric" required /></label></> : null}
      {scope.scopeLevel === "全国" ? <small>覆盖全国，无需填写省市。</small> : null}
    </fieldset>)}
  </div>;
}

/** 删除确认使用原生模态语义，并保留服务端最终权限校验。 */
function AccountDeleteDialog({ user, onCancel, onDeleted }: { user: AuthorizedUser; onCancel: () => void; onDeleted: (id: string) => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => { if (dialog?.open) dialog.close(); };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch<void>(`/authorized-users/${user.id}`, { method: "DELETE" });
      onDeleted(user.id);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "删除账号失败");
      setSubmitting(false);
    }
  }

  return <dialog ref={dialogRef} className="organization-delete-dialog" aria-labelledby="account-delete-title" onCancel={(event) => { event.preventDefault(); if (!submitting) onCancel(); }}><form onSubmit={submit}><div className="delete-dialog-icon"><Trash2 size={22} /></div><h2 id="account-delete-title">删除授权账号？</h2><p>删除“{user.username}”后，该账号全部登录会话会立即失效，且无法再进入网站。</p>{error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={submitting} autoFocus>取消</button><button className="organization-dialog-save" disabled={submitting}>{submitting ? "正在删除…" : "确认删除"}</button></footer></form></dialog>;
}

/** 修改普通用户状态和全部覆盖范围；受保护账号不打开该对话框。 */
function AccountEditDialog({ user, salespeople, onCancel, onSaved }: { user: AuthorizedUser; salespeople: SalespersonOption[]; onCancel: () => void; onSaved: (user: AuthorizedUser) => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [isActive, setIsActive] = useState(user.is_active);
  const [scopes, setScopes] = useState<ScopeDraft[]>(() => user.coverage_scopes.map(scopeDraft));
  const [salespersonId, setSalespersonId] = useState(user.salesperson_id ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => { if (dialog?.open) dialog.close(); };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      onSaved(await apiFetch<AuthorizedUser>(`/authorized-users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: isActive, salesperson_id: salespersonId || null, coverage_scopes: scopePayload(scopes) }),
      }));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "修改账号失败");
      setSubmitting(false);
    }
  }

  return <dialog ref={dialogRef} className="organization-edit-dialog account-edit-dialog" aria-labelledby="account-edit-title" onCancel={(event) => { event.preventDefault(); if (!submitting) onCancel(); }}><form onSubmit={submit}><header><div><span>账号权限</span><h2 id="account-edit-title">修改 {user.username}</h2></div></header><label className="account-active-toggle"><input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />允许该账号登录</label><label>关联销售人员{requiresLinkedSalesperson(scopes) ? " *" : ""}<select value={salespersonId} onChange={(event) => setSalespersonId(event.target.value)} required={requiresLinkedSalesperson(scopes)}><option value="">未关联</option>{salespeople.map((salesperson) => <option key={salesperson.value} value={salesperson.value}>{salesperson.label}</option>)}</select><small>区域账号在销售覆盖与人效页只显示该人员的 Pin。</small></label><AccountScopeEditor scopes={scopes} onChange={setScopes} />{error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={submitting}>取消</button><button className="organization-dialog-save" disabled={submitting || scopes.length === 0 || (requiresLinkedSalesperson(scopes) && !salespersonId)}>{submitting ? "正在保存…" : "保存权限"}</button></footer></form></dialog>;
}

/** 管理账号列表、新增凭据、启用状态和多个四级覆盖范围。 */
export function AdminAccountWorkspace() {
  const [users, setUsers] = useState<AuthorizedUser[]>([]);
  const [salespeople, setSalespeople] = useState<SalespersonOption[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [salespersonId, setSalespersonId] = useState("");
  const [scopes, setScopes] = useState<ScopeDraft[]>([emptyScope()]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<AuthorizedUser | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AuthorizedUser | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedUsers, loadedSalespeople] = await Promise.all([
        apiFetch<AuthorizedUser[]>("/authorized-users"),
        apiFetch<SalespersonOption[]>("/admin-data/salespeople/options"),
      ]);
      setUsers(loadedUsers);
      setSalespeople(loadedSalespeople);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "授权账号加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => void loadUsers(), 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadUsers]);

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const created = await apiFetch<AuthorizedUser>("/authorized-users", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password, salesperson_id: salespersonId || null, coverage_scopes: scopePayload(scopes) }),
      });
      setUsers((current) => [...current, created].sort((left, right) => left.username.localeCompare(right.username)));
      setUsername("");
      setPassword("");
      setSalespersonId("");
      setScopes([emptyScope()]);
      setNotice(`已添加普通用户 ${created.username}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "添加账号失败");
    } finally {
      setSubmitting(false);
    }
  }

  return <section className="account-admin-workspace">
    <form className="account-create-card" onSubmit={createUser}>
      <div className="account-section-heading"><div><span>访问授权</span><h2>添加普通用户</h2><p>范围先用于账号配置；第二阶段启用业务数据区域校验。</p></div><KeyRound size={22} /></div>
      <label>账号<input value={username} onChange={(event) => setUsername(event.target.value)} minLength={3} maxLength={80} pattern="[A-Za-z0-9._-]+" autoComplete="off" required placeholder="例如 jilin_sales" /></label>
      <label>初始密码<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" minLength={12} maxLength={128} autoComplete="new-password" required placeholder="至少 12 位" /></label>
      <label>关联销售人员{requiresLinkedSalesperson(scopes) ? " *" : ""}<select value={salespersonId} onChange={(event) => setSalespersonId(event.target.value)} required={requiresLinkedSalesperson(scopes)}><option value="">未关联</option>{salespeople.map((salesperson) => <option key={salesperson.value} value={salesperson.value}>{salesperson.label}</option>)}</select><small>区域账号只能查看所关联销售人员的 Pin；全国账号查看全部。</small></label>
      <AccountScopeEditor scopes={scopes} onChange={setScopes} />
      <button className="admin-primary" disabled={submitting || scopes.length === 0 || (requiresLinkedSalesperson(scopes) && !salespersonId)}><Plus size={15} />{submitting ? "正在添加…" : "添加授权账号"}</button>
    </form>

    <div className="account-list-card">
      <div className="account-section-heading"><div><span>账号目录</span><h2>{loading ? "正在加载…" : `${users.length} 个授权账号`}</h2><p>超级管理员固定为全国范围；普通用户可配置多个市、省或大区。</p></div><ShieldCheck size={22} /></div>
      {notice ? <p className="admin-page-notice" role="status">{notice}</p> : null}
      {error ? <p className="admin-page-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
      <div className="account-list" aria-busy={loading}>
        {users.map((user) => <article key={user.id} className="account-row"><div className={`account-avatar ${user.is_protected ? "admin" : ""}`}>{user.is_protected ? <ShieldCheck size={18} /> : <UserRound size={18} />}</div><div className="account-identity"><strong>{user.username}{user.is_current ? <small>当前账号</small> : null}</strong><span>{user.role} · {user.is_active ? "已启用" : "已停用"}</span>{user.salesperson_name ? <span>关联销售：{user.salesperson_name}{user.salesperson_employee_code ? `（${user.salesperson_employee_code}）` : ""}</span> : null}</div><div className="account-scope-list">{user.coverage_scopes.map((scope) => <span key={scope.id}>{scope.scope_name}{scope.scope_level === "全国" ? null : <small>{scope.scope_level === "大区" ? "大区" : `${scope.scope_level}级`}</small>}</span>)}</div><time>最近登录：{formatAccountTime(user.last_login_at)}</time><div className="account-row-actions"><button type="button" onClick={() => setEditTarget(user)} disabled={user.is_protected} title={user.is_protected ? "超级管理员权限固定" : `修改 ${user.username}`}><Pencil size={14} />修改</button><button type="button" onClick={() => setDeleteTarget(user)} disabled={user.is_protected} title={user.is_protected ? "超级管理员账号受保护" : `删除 ${user.username}`}><Trash2 size={14} />删除</button></div></article>)}
        {!loading && users.length === 0 ? <p className="account-empty">暂无授权账号。</p> : null}
      </div>
    </div>
    {editTarget ? <AccountEditDialog user={editTarget} salespeople={salespeople} onCancel={() => setEditTarget(null)} onSaved={(updated) => { setUsers((current) => current.map((user) => user.id === updated.id ? updated : user)); setEditTarget(null); setNotice(`已更新 ${updated.username} 的覆盖范围`); }} /> : null}
    {deleteTarget ? <AccountDeleteDialog user={deleteTarget} onCancel={() => setDeleteTarget(null)} onDeleted={(id) => { setUsers((current) => current.filter((user) => user.id !== id)); setDeleteTarget(null); setNotice("授权账号已删除"); }} /> : null}
  </section>;
}
