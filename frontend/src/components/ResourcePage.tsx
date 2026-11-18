import { useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { useDebounce } from '@/hooks/useDebounce';
import { usePagedList } from '@/hooks/useFetch';
import type { Params } from '@/hooks/useFetch';
import { parseError } from '@/utils/errors';
import { Card, PageHeader } from './ui/Card';
import { DataTable } from './ui/DataTable';
import type { Column } from './ui/DataTable';
import { Field, FormError, SearchInput, inputClass } from './ui/Form';
import { ConfirmDialog, Modal } from './ui/Modal';
import { Pagination } from './ui/Pagination';

export interface FieldDef {
  name: string;
  label: string;
  type?: 'text' | 'email' | 'textarea' | 'password' | 'select' | 'checkbox';
  required?: boolean;
  options?: { value: string; label: string }[];
  showOn?: 'create' | 'edit' | 'both';
  placeholder?: string;
  hint?: string;
  half?: boolean; // দুই কলামে দেখানোর জন্য
}

type FormValues = Record<string, string | boolean>;

interface Props<T extends { id: number }> {
  title: string;
  subtitle: string;
  singular: string;
  endpoint: string; // যেমন '/categories/'
  columns: Column<T>[];
  fields: FieldDef[];
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
  searchPlaceholder?: string;
  defaults?: FormValues;
  filters?: ReactNode;
  filterParams?: Params;
  deleteMessage?: (row: T) => ReactNode;
  /** প্রতিটি row-এর Edit/Delete বোতামের আগে অতিরিক্ত বোতাম (যেমন Approve) */
  extraActions?: (row: T, reload: () => void) => ReactNode;
}

/** Categories / Suppliers / Customers / Users — সব CRUD পেজের জন্য একটি সাধারণ কম্পোনেন্ট */
export function ResourcePage<T extends { id: number }>({
  title,
  subtitle,
  singular,
  endpoint,
  columns,
  fields,
  canCreate,
  canEdit,
  canDelete,
  searchPlaceholder = 'Search…',
  defaults = {},
  filters,
  filterParams = {},
  deleteMessage,
  extraActions,
}: Props<T>) {
  const [search, setSearch] = useState('');
  const debounced = useDebounce(search);
  const list = usePagedList<T>(endpoint, { search: debounced, ...filterParams });

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<T | null>(null);
  const [values, setValues] = useState<FormValues>({});
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const [deleting, setDeleting] = useState<T | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const visibleFields = fields.filter(
    (f) => !f.showOn || f.showOn === 'both' || (editing ? f.showOn === 'edit' : f.showOn === 'create'),
  );

  const openCreate = () => {
    const initial: FormValues = {};
    fields.forEach((f) => {
      initial[f.name] = f.type === 'checkbox' ? true : '';
    });
    setEditing(null);
    setValues({ ...initial, ...defaults });
    setFormError('');
    setFieldErrors({});
    setFormOpen(true);
  };

  const openEdit = (row: T) => {
    const record = row as unknown as Record<string, unknown>;
    const initial: FormValues = {};
    fields.forEach((f) => {
      const v = record[f.name];
      if (f.type === 'checkbox') initial[f.name] = Boolean(v);
      else if (f.type === 'password') initial[f.name] = '';
      else initial[f.name] = v == null ? '' : String(v);
    });
    setEditing(row);
    setValues(initial);
    setFormError('');
    setFieldErrors({});
    setFormOpen(true);
  };

  const closeForm = () => {
    if (!saving) setFormOpen(false);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFormError('');
    setFieldErrors({});

    const payload: Record<string, unknown> = {};
    visibleFields.forEach((f) => {
      const v = values[f.name];
      if (f.type === 'password' && editing && !v) return; // খালি থাকলে পাসওয়ার্ড বদলাবে না
      payload[f.name] = v;
    });

    try {
      if (editing) {
        await api.patch(`${endpoint}${editing.id}/`, payload);
        toast.success(`${singular} updated`);
      } else {
        await api.post(endpoint, payload);
        toast.success(`${singular} created`);
      }
      setFormOpen(false);
      list.reload();
    } catch (err) {
      const parsed = parseError(err);
      setFieldErrors(parsed.fields);
      const hasFieldMatch = Object.keys(parsed.fields).some((k) => visibleFields.some((f) => f.name === k));
      setFormError(hasFieldMatch ? '' : parsed.message);
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await api.delete(`${endpoint}${deleting.id}/`);
      toast.success(`${singular} deleted`);
      setDeleting(null);
      // শেষ পাতার একমাত্র রেকর্ড মুছলে আগের পাতায় যাই
      if (list.data && list.data.results.length === 1 && list.page > 1) list.setPage(list.page - 1);
      else list.reload();
    } catch (err) {
      toast.error(parseError(err).message);
      setDeleting(null);
    } finally {
      setDeleteBusy(false);
    }
  };

  const allColumns: Column<T>[] = [...columns];
  if (canEdit || canDelete || extraActions) {
    allColumns.push({
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) => (
        <div className="flex items-center justify-end gap-1">
          {extraActions?.(row, list.reload)}
          {canEdit && (
            <button className="btn-icon" title="Edit" onClick={() => openEdit(row)}>
              <Pencil className="h-4 w-4" />
            </button>
          )}
          {canDelete && (
            <button className="btn-icon hover:!bg-red-50 hover:!text-red-600" title="Delete" onClick={() => setDeleting(row)}>
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      ),
    });
  }

  const setValue = (name: string, v: string | boolean) => setValues((prev) => ({ ...prev, [name]: v }));

  return (
    <>
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={
          canCreate && (
            <button className="btn btn-primary" onClick={openCreate}>
              <Plus className="h-4 w-4" /> Add {singular}
            </button>
          )
        }
      />

      <Card bodyClassName="p-0">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center">
          <SearchInput value={search} onChange={setSearch} placeholder={searchPlaceholder} className="sm:w-80" />
          {filters}
        </div>
        <DataTable
          columns={allColumns}
          rows={list.data?.results ?? []}
          rowKey={(r) => r.id}
          loading={list.loading}
          error={list.error}
          onRetry={list.reload}
          emptyTitle={`No ${title.toLowerCase()} found`}
          emptyDescription={search ? 'Try a different search term.' : undefined}
          emptyAction={
            canCreate && !search ? (
              <button className="btn btn-primary btn-sm" onClick={openCreate}>
                <Plus className="h-4 w-4" /> Add {singular}
              </button>
            ) : undefined
          }
        />
        <Pagination page={list.page} count={list.data?.count ?? 0} onChange={list.setPage} />
      </Card>

      <Modal
        open={formOpen}
        onClose={closeForm}
        title={editing ? `Edit ${singular}` : `Add ${singular}`}
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={closeForm} disabled={saving}>
              Cancel
            </button>
            <button type="submit" form="resource-form" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : editing ? 'Save changes' : `Create ${singular.toLowerCase()}`}
            </button>
          </>
        }
      >
        <form id="resource-form" onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2 [&:empty]:hidden">
            <FormError message={formError} />
          </div>
          {visibleFields.map((f) => {
            const err = fieldErrors[f.name];
            const span = f.half ? '' : 'sm:col-span-2';
            if (f.type === 'checkbox') {
              return (
                <label key={f.name} className={`flex items-center gap-2 text-sm text-slate-700 ${span}`}>
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    checked={Boolean(values[f.name])}
                    onChange={(e) => setValue(f.name, e.target.checked)}
                  />
                  {f.label}
                </label>
              );
            }
            const required = f.required && !(f.type === 'password' && editing);
            return (
              <Field
                key={f.name}
                label={f.label}
                required={required}
                error={err}
                hint={f.type === 'password' && editing ? 'Leave blank to keep the current password.' : f.hint}
                className={span}
              >
                {f.type === 'textarea' ? (
                  <textarea
                    className={inputClass(err)}
                    rows={3}
                    placeholder={f.placeholder}
                    value={String(values[f.name] ?? '')}
                    onChange={(e) => setValue(f.name, e.target.value)}
                  />
                ) : f.type === 'select' ? (
                  <select
                    className={inputClass(err)}
                    value={String(values[f.name] ?? '')}
                    onChange={(e) => setValue(f.name, e.target.value)}
                  >
                    {f.options?.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={f.type ?? 'text'}
                    className={inputClass(err)}
                    placeholder={f.placeholder}
                    autoComplete={f.type === 'password' ? 'new-password' : 'off'}
                    required={required}
                    value={String(values[f.name] ?? '')}
                    onChange={(e) => setValue(f.name, e.target.value)}
                  />
                )}
              </Field>
            );
          })}
        </form>
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title={`Delete ${singular.toLowerCase()}?`}
        message={
          deleting && deleteMessage
            ? deleteMessage(deleting)
            : `This ${singular.toLowerCase()} will be permanently deleted. This action cannot be undone.`
        }
        loading={deleteBusy}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </>
  );
}
