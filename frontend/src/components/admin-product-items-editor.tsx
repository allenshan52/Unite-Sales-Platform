/** 可复用的成交产品明细编辑器：维护名称、品牌、规格、单价、数量与分项总价。 */

import { Plus, Trash2 } from "lucide-react";

export interface ProductItemDraft {
  draftKey: string;
  id: string | null;
  productName: string;
  brand: string;
  specificationModel: string;
  productImageUrl: string;
  unitPrice: string;
  quantity: string;
  lineTotal: string;
}

/** 创建一条隔离的空产品草稿，避免多个订单共享可变状态。 */
export function emptyProductItem(): ProductItemDraft {
  return {
    draftKey: crypto.randomUUID(), id: null, productName: "", brand: "", specificationModel: "",
    productImageUrl: "", unitPrice: "", quantity: "", lineTotal: "",
  };
}

/** 把 API 的蛇形字段转换成表单草稿。 */
export function productItemFromApi(value: Record<string, unknown>): ProductItemDraft {
  return {
    draftKey: String(value.id ?? crypto.randomUUID()),
    id: value.id ? String(value.id) : null,
    productName: String(value.product_name ?? ""),
    brand: String(value.brand ?? ""),
    specificationModel: String(value.specification_model ?? ""),
    productImageUrl: String(value.product_image_url ?? ""),
    unitPrice: String(value.unit_price ?? ""),
    quantity: String(value.quantity ?? ""),
    lineTotal: String(value.line_total ?? ""),
  };
}

/** 把产品草稿转换为后端可校验的金额和可空文本字段。 */
export function productItemPayload(value: ProductItemDraft): Record<string, unknown> {
  const optionalText = (text: string) => text.trim() || null;
  const optionalNumber = (text: string) => text.trim() ? Number(text) : null;
  return {
    id: value.id,
    product_name: value.productName.trim(),
    brand: optionalText(value.brand),
    specification_model: optionalText(value.specificationModel),
    product_image_url: optionalText(value.productImageUrl),
    unit_price: optionalNumber(value.unitPrice),
    quantity: optionalNumber(value.quantity),
    line_total: Number(value.lineTotal),
  };
}

/** 渲染可增删的产品行；同行订单可额外维护产品图片地址。 */
export function AdminProductItemsEditor({ value, onChange, showImage = false }: { value: ProductItemDraft[]; onChange: (value: ProductItemDraft[]) => void; showImage?: boolean }) {
  const update = (index: number, patch: Partial<ProductItemDraft>) => onChange(value.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  return (
    <div className="admin-product-editor field-wide">
      <div className="admin-product-editor-head"><span>产品明细</span><button type="button" onClick={() => onChange([...value, emptyProductItem()])}><Plus size={14} />添加产品</button></div>
      {value.length === 0 ? <p>尚未添加产品。</p> : null}
      {value.map((item, index) => (
        <article key={item.draftKey}>
          <header><strong>产品 {index + 1}</strong><button type="button" onClick={() => onChange(value.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={13} />移除</button></header>
          <div className="organization-edit-grid">
            <label><span>产品名称<b aria-hidden="true">*</b></span><input value={item.productName} onChange={(event) => update(index, { productName: event.target.value })} maxLength={255} required /></label>
            <label><span>品牌</span><input value={item.brand} onChange={(event) => update(index, { brand: event.target.value })} maxLength={255} /></label>
            <label><span>产品规格</span><input value={item.specificationModel} onChange={(event) => update(index, { specificationModel: event.target.value })} maxLength={255} /></label>
            <label><span>单价（元）</span><input type="number" min="0.01" step="0.01" value={item.unitPrice} onChange={(event) => update(index, { unitPrice: event.target.value })} /></label>
            <label><span>数量</span><input type="number" min="0.001" step="0.001" value={item.quantity} onChange={(event) => update(index, { quantity: event.target.value })} /></label>
            <label><span>产品总价（元）<b aria-hidden="true">*</b></span><input type="number" min="0" step="0.01" value={item.lineTotal} onChange={(event) => update(index, { lineTotal: event.target.value })} required /></label>
            {showImage ? <label className="field-wide"><span>产品图片路径或 URL</span><input value={item.productImageUrl} onChange={(event) => update(index, { productImageUrl: event.target.value })} maxLength={1000} /></label> : null}
          </div>
        </article>
      ))}
    </div>
  );
}
