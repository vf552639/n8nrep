import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import toast from "react-hot-toast";
import { authorsApi } from "@/api/authors";
import { Author, AuthorFormPayload } from "@/types/author";
import { ReactTable } from "@/components/common/ReactTable";
import { Plus, User, X } from "lucide-react";

const EMPTY_FORM: AuthorFormPayload = {
  author: "",
  country: "",
  country_full: "",
  language: "",
  bio: "",
  co_short: "",
  city: "",
  imitation: "",
  year: "",
  face: "",
  target_audience: "",
  rhythms_style: "",
  exclude_words: "",
};

function authorToForm(a: Author): AuthorFormPayload {
  return {
    author: a.author ?? "",
    country: a.country ?? "",
    country_full: a.country_full ?? "",
    language: a.language ?? "",
    bio: a.bio ?? "",
    co_short: a.co_short ?? "",
    city: a.city ?? "",
    imitation: a.imitation ?? "",
    year: a.year != null ? formatYearCell(a.year) : "",
    face: a.face ?? "",
    target_audience: a.target_audience ?? "",
    rhythms_style: a.rhythms_style ?? "",
    exclude_words: a.exclude_words ?? "",
  };
}

/** Renders year without trailing `.0` from float-like values */
function formatYearCell(v: unknown): string {
  if (v === null || v === undefined) return "—";
  const s = String(v).trim();
  if (s === "") return "—";
  const num = Number(s);
  if (Number.isFinite(num)) {
    return String(Math.round(num));
  }
  return s;
}

function AuthorFormFields({
  formData,
  setFormData,
}: {
  formData: AuthorFormPayload;
  setFormData: React.Dispatch<React.SetStateAction<AuthorFormPayload>>;
}) {
  const field = (key: keyof AuthorFormPayload) => ({
    value: formData[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setFormData((prev) => ({ ...prev, [key]: e.target.value })),
  });

  return (
    <div className="space-y-6 max-h-[70vh] overflow-y-auto pr-1">
      <div>
        <h3 className="text-sm font-semibold text-slate-800 border-b pb-2 mb-3">Основные данные</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Имя автора *</label>
            <input
              required
              type="text"
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
              {...field("author")}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Страна *</label>
              <input
                required
                type="text"
                placeholder="e.g. Australia"
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
                {...field("country")}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Язык *</label>
              <input
                required
                type="text"
                placeholder="e.g. English"
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
                {...field("language")}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Страна (полное название, например: United Kingdom)
            </label>
            <input
              type="text"
              placeholder="e.g. Germany, United Kingdom"
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
              {...field("country_full")}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Код страны</label>
              <input
                type="text"
                placeholder="e.g. AU, DE"
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
                {...field("co_short")}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Город</label>
              <input
                type="text"
                className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
                {...field("city")}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Биография / описание</label>
            <textarea
              rows={3}
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
              {...field("bio")}
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-800 border-b pb-2 mb-3">Стилистика (Tone of Voice)</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Imitation (Mimicry)</label>
            <p className="text-xs text-slate-500 mb-1">Кого подражать</p>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
              {...field("imitation")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Год / эпоха стиля</label>
            <input
              type="text"
              placeholder="e.g. 2024"
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
              {...field("year")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Face / лицо</label>
            <input
              type="text"
              placeholder="e.g. Friendly, Expert"
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
              {...field("face")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Целевая аудитория</label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
              {...field("target_audience")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Ритм и стиль</label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
              {...field("rhythms_style")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Exclude words</label>
            <textarea
              rows={2}
              className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
              placeholder="word1, word2"
              {...field("exclude_words")}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AuthorsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editAuthor, setEditAuthor] = useState<Author | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["authors"],
    queryFn: async () => authorsApi.getAll({ limit: 1000 }),
  });

  const columns = useMemo(
    () => [
      {
        accessorKey: "author",
        header: "Author",
        cell: ({ row }: { row: { original: Author } }) => (
          <div className="font-semibold text-slate-800 flex items-center gap-2">
            <User className="w-4 h-4 text-slate-400" /> {row.original.author}
          </div>
        ),
      },
      {
        accessorKey: "country",
        header: "Country",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="bg-slate-100 px-2 py-0.5 rounded text-sm uppercase">{row.original.country}</span>
        ),
      },
      {
        accessorKey: "language",
        header: "Language",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="bg-slate-100 px-2 py-0.5 rounded text-sm lowercase">{row.original.language}</span>
        ),
      },
      {
        accessorKey: "city",
        header: "City",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="text-xs text-slate-600 max-w-[120px] truncate block" title={row.original.city}>
            {row.original.city || "—"}
          </span>
        ),
      },
      {
        accessorKey: "imitation",
        header: "Imitation",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="text-xs text-slate-600 max-w-[140px] truncate" title={row.original.imitation}>
            {row.original.imitation || "—"}
          </span>
        ),
      },
      {
        accessorKey: "year",
        header: "Year",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="text-xs text-slate-600">{formatYearCell(row.original.year)}</span>
        ),
      },
      {
        accessorKey: "face",
        header: "Face",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="text-xs text-slate-600 max-w-[100px] truncate" title={row.original.face}>
            {row.original.face || "—"}
          </span>
        ),
      },
      {
        accessorKey: "target_audience",
        header: "Target audience",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="text-xs text-slate-600 max-w-[140px] truncate" title={row.original.target_audience}>
            {row.original.target_audience || "—"}
          </span>
        ),
      },
      {
        accessorKey: "rhythms_style",
        header: "Style",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="text-xs text-slate-600 max-w-[140px] truncate" title={row.original.rhythms_style}>
            {row.original.rhythms_style || "—"}
          </span>
        ),
      },
      {
        accessorKey: "usage_count",
        header: "Tasks",
        cell: ({ row }: { row: { original: Author } }) => (
          <span className="tabular-nums font-medium text-slate-700">{row.original.usage_count ?? 0}</span>
        ),
      },
    ],
    []
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl border shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-indigo-500 pl-3">Authors</h1>
          <p className="text-sm text-slate-500 mt-1 pl-4">Авторы и стилистика генерации.</p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" /> Add Author
        </button>
      </div>

      <ReactTable
        columns={columns as any}
        data={data || []}
        isLoading={isLoading}
        onRowClick={(a: Author) => setEditAuthor(a)}
      />

      {isCreateOpen && <CreateAuthorModal onClose={() => setIsCreateOpen(false)} />}
      {editAuthor && <EditAuthorModal author={editAuthor} onClose={() => setEditAuthor(null)} />}
    </div>
  );
}

function CreateAuthorModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<AuthorFormPayload>({ ...EMPTY_FORM });

  const mutation = useMutation({
    mutationFn: (data: AuthorFormPayload) => authorsApi.create(data),
    onSuccess: () => {
      toast.success("Author created successfully");
      queryClient.invalidateQueries({ queryKey: ["authors"] });
      onClose();
    },
    onError: () => toast.error("Failed to create author"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.author) {
      toast.error("Author name is required");
      return;
    }
    mutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[95vh]">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center shrink-0">
          <h2 className="text-lg font-bold text-slate-900">Add New Author</h2>
          <button type="button" onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="p-6 overflow-y-auto flex-1">
            <AuthorFormFields formData={formData} setFormData={setFormData} />
          </div>
          <div className="flex justify-end gap-3 px-6 py-4 border-t bg-slate-50 shrink-0">
            <button type="button" onClick={onClose} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg text-sm font-medium">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 text-sm font-medium disabled:opacity-50"
            >
              {mutation.isPending ? "Saving..." : "Save Author"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditAuthorModal({ author, onClose }: { author: Author; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<AuthorFormPayload>(() => authorToForm(author));

  const mutation = useMutation({
    mutationFn: (data: AuthorFormPayload) => authorsApi.update(author.id, data),
    onSuccess: () => {
      toast.success("Author updated");
      queryClient.invalidateQueries({ queryKey: ["authors"] });
      onClose();
    },
    onError: () => toast.error("Failed to update author"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.author) {
      toast.error("Author name is required");
      return;
    }
    mutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[95vh]">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center shrink-0">
          <h2 className="text-lg font-bold text-slate-900">Edit Author</h2>
          <button type="button" onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="p-6 overflow-y-auto flex-1">
            <AuthorFormFields formData={formData} setFormData={setFormData} />
          </div>
          <div className="flex justify-end gap-3 px-6 py-4 border-t bg-slate-50 shrink-0">
            <button type="button" onClick={onClose} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg text-sm font-medium">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 text-sm font-medium disabled:opacity-50"
            >
              {mutation.isPending ? "Saving..." : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
