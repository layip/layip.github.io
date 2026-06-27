<?php
/**
 * SENTINEL - PHP standalone safe conversion
 * Chạy: php -S localhost:8000 122.php
 * Không có Telegram bot, không thu thập camera/vị trí/IP, chỉ quản lý link và đếm lượt mở.
 */
declare(strict_types=1);
session_start();

const DB_FILE = __DIR__ . '/sentinel.sqlite';
const ADMIN_PASS = '123';

function db(): PDO {
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }
    $pdo = new PDO('sqlite:' . DB_FILE);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->exec("CREATE TABLE IF NOT EXISTS links (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        image TEXT NOT NULL DEFAULT '',
        redirect_url TEXT NOT NULL DEFAULT '',
        clicks INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )");
    $pdo->exec("CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    )");
    seed_settings($pdo);
    return $pdo;
}

function seed_settings(PDO $pdo): void {
    $defaults = [
        'root_title' => 'Security Sync',
        'root_desc' => 'Identity Verification Required',
        'root_img' => 'https://www.gstatic.com/images/branding/product/2x/photos_96dp.png',
        'root_redir' => 'https://google.com',
        'ui_msg' => 'ĐANG LOADING...',
        'ui_st' => 'KIỂM TRA TRÌNH DUYỆT',
        'btn_text' => 'TIẾP TỤC',
    ];
    $stmt = $pdo->prepare('INSERT OR IGNORE INTO settings (key, value) VALUES (:key, :value)');
    foreach ($defaults as $key => $value) {
        $stmt->execute([':key' => $key, ':value' => $value]);
    }
}

function setting(string $key): string {
    $stmt = db()->prepare('SELECT value FROM settings WHERE key = :key');
    $stmt->execute([':key' => $key]);
    $value = $stmt->fetchColumn();
    return is_string($value) ? $value : '';
}

function set_setting(string $key, string $value): void {
    $stmt = db()->prepare('INSERT INTO settings (key, value) VALUES (:key, :value)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value');
    $stmt->execute([':key' => $key, ':value' => $value]);
}

function h(?string $value): string {
    return htmlspecialchars($value ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function make_id(string $url): string {
    $host = parse_url($url, PHP_URL_HOST) ?: 'link';
    $slug = preg_replace('/[^a-z0-9]+/i', '-', strtolower((string) $host));
    $slug = trim((string) $slug, '-') ?: 'link';
    return substr($slug, 0, 24) . '-' . bin2hex(random_bytes(3));
}

function current_url(array $params = []): string {
    $scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
    $host = $_SERVER['HTTP_HOST'] ?? 'localhost';
    $path = strtok($_SERVER['REQUEST_URI'] ?? '/122.php', '?');
    $query = $params ? '?' . http_build_query($params) : '';
    return $scheme . '://' . $host . $path . $query;
}

function redirect_to(string $url): never {
    header('Location: ' . $url, true, 302);
    exit;
}

$action = $_GET['action'] ?? '';
if ($action === 'logout') {
    unset($_SESSION['sentinel_auth']);
    redirect_to(current_url(['admin' => '1']));
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    handle_post();
}

if (isset($_GET['admin'])) {
    render_admin();
    exit;
}

render_public();

function handle_post(): void {
    if (isset($_POST['login'])) {
        if (hash_equals(ADMIN_PASS, (string) ($_POST['password'] ?? ''))) {
            $_SESSION['sentinel_auth'] = true;
        }
        redirect_to(current_url(['admin' => '1']));
    }

    if (empty($_SESSION['sentinel_auth'])) {
        redirect_to(current_url(['admin' => '1']));
    }

    if (isset($_POST['save_settings'])) {
        foreach (['root_title', 'root_desc', 'root_img', 'root_redir', 'ui_msg', 'ui_st', 'btn_text'] as $key) {
            set_setting($key, trim((string) ($_POST[$key] ?? '')));
        }
        redirect_to(current_url(['admin' => '1', 'tab' => 'settings']));
    }

    if (isset($_POST['save_link'])) {
        $id = trim((string) ($_POST['id'] ?? ''));
        $redirectUrl = trim((string) ($_POST['redirect_url'] ?? ''));
        if ($id === '') {
            $id = make_id($redirectUrl);
        }
        $stmt = db()->prepare('INSERT INTO links (id, title, description, image, redirect_url) VALUES (:id, :title, :description, :image, :redirect_url)
            ON CONFLICT(id) DO UPDATE SET title = excluded.title, description = excluded.description, image = excluded.image, redirect_url = excluded.redirect_url');
        $stmt->execute([
            ':id' => $id,
            ':title' => trim((string) ($_POST['title'] ?? '')),
            ':description' => trim((string) ($_POST['description'] ?? '')),
            ':image' => trim((string) ($_POST['image'] ?? '')),
            ':redirect_url' => $redirectUrl,
        ]);
        redirect_to(current_url(['admin' => '1']));
    }

    if (isset($_POST['delete_link'])) {
        $stmt = db()->prepare('DELETE FROM links WHERE id = :id');
        $stmt->execute([':id' => (string) ($_POST['id'] ?? '')]);
        redirect_to(current_url(['admin' => '1']));
    }

    redirect_to(current_url(['admin' => '1']));
}

function render_public(): void {
    $linkId = trim((string) ($_GET['v'] ?? ''));
    $link = null;
    if ($linkId !== '') {
        $stmt = db()->prepare('SELECT * FROM links WHERE id = :id');
        $stmt->execute([':id' => $linkId]);
        $link = $stmt->fetch(PDO::FETCH_ASSOC) ?: null;
        if ($link) {
            $update = db()->prepare('UPDATE links SET clicks = clicks + 1 WHERE id = :id');
            $update->execute([':id' => $linkId]);
        }
    }

    $title = $link['title'] ?? setting('root_title');
    $desc = $link['description'] ?? setting('root_desc');
    $img = $link['image'] ?? setting('root_img');
    $redir = $link['redirect_url'] ?? setting('root_redir');
    ?>
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= h($title) ?></title>
  <meta name="description" content="<?= h($desc) ?>">
  <meta property="og:title" content="<?= h($title) ?>">
  <meta property="og:description" content="<?= h($desc) ?>">
  <meta property="og:image" content="<?= h($img) ?>">
  <style><?= base_css() ?></style>
</head>
<body class="public">
  <main class="verify-card">
    <div class="loader" aria-hidden="true"></div>
    <p class="eyebrow"><?= h(setting('ui_msg')) ?></p>
    <h1><?= h($title) ?></h1>
    <p><?= h($desc) ?></p>
    <?php if ($img !== ''): ?><img class="preview" src="<?= h($img) ?>" alt="Ảnh minh họa"><?php endif; ?>
    <p class="safe-note">Trang PHP này không dùng bot, không lấy camera, không lấy GPS và không gửi dữ liệu người xem ra dịch vụ ngoài.</p>
    <a class="button" href="<?= h($redir) ?>" rel="nofollow noopener"><?= h(setting('btn_text')) ?></a>
  </main>
</body>
</html>
    <?php
}

function render_admin(): void {
    if (empty($_SESSION['sentinel_auth'])) {
        render_login();
        return;
    }

    $edit = null;
    if (!empty($_GET['edit'])) {
        $stmt = db()->prepare('SELECT * FROM links WHERE id = :id');
        $stmt->execute([':id' => (string) $_GET['edit']]);
        $edit = $stmt->fetch(PDO::FETCH_ASSOC) ?: null;
    }
    $links = db()->query('SELECT * FROM links ORDER BY clicks DESC, created_at DESC')->fetchAll(PDO::FETCH_ASSOC);
    ?>
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Admin - Sentinel PHP</title>
  <style><?= base_css() ?></style>
</head>
<body>
  <div class="admin-layout">
    <aside class="sidebar">
      <h1>SENTINEL PHP</h1>
      <p>Full code PHP, không bot.</p>
      <a class="button secondary" href="<?= h(current_url()) ?>">Xem trang public</a>
      <a class="danger-link" href="<?= h(current_url(['action' => 'logout'])) ?>">Đăng xuất</a>
    </aside>

    <main class="admin-main">
      <section class="panel">
        <h2><?= $edit ? 'Sửa link' : 'Tạo link' ?></h2>
        <form method="post" class="form-grid">
          <input type="hidden" name="save_link" value="1">
          <label>ID<input name="id" value="<?= h($edit['id'] ?? '') ?>" placeholder="Tự tạo nếu bỏ trống" <?= $edit ? 'readonly' : '' ?>></label>
          <label>Tiêu đề<input name="title" value="<?= h($edit['title'] ?? '') ?>" required></label>
          <label>Mô tả<textarea name="description" rows="3"><?= h($edit['description'] ?? '') ?></textarea></label>
          <label>Ảnh OG<input name="image" value="<?= h($edit['image'] ?? '') ?>" placeholder="https://..."></label>
          <label>Redirect URL<input name="redirect_url" value="<?= h($edit['redirect_url'] ?? '') ?>" placeholder="https://..." required></label>
          <button class="button" type="submit">Lưu link</button>
        </form>
      </section>

      <section class="panel">
        <h2>Cấu hình trang mặc định</h2>
        <form method="post" class="form-grid">
          <input type="hidden" name="save_settings" value="1">
          <label>Root title<input name="root_title" value="<?= h(setting('root_title')) ?>"></label>
          <label>Root desc<textarea name="root_desc" rows="2"><?= h(setting('root_desc')) ?></textarea></label>
          <label>Root image<input name="root_img" value="<?= h(setting('root_img')) ?>"></label>
          <label>Root redirect<input name="root_redir" value="<?= h(setting('root_redir')) ?>"></label>
          <label>Loading text<input name="ui_msg" value="<?= h(setting('ui_msg')) ?>"></label>
          <label>Status text<input name="ui_st" value="<?= h(setting('ui_st')) ?>"></label>
          <label>Button text<input name="btn_text" value="<?= h(setting('btn_text')) ?>"></label>
          <button class="button" type="submit">Lưu cấu hình</button>
        </form>
      </section>

      <section class="panel full">
        <h2>Danh sách link</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Meta</th><th>URL</th><th>Lượt mở</th><th>Hành động</th></tr></thead>
            <tbody>
            <?php foreach ($links as $link): ?>
              <?php $publicUrl = current_url(['v' => $link['id']]); ?>
              <tr>
                <td><strong><?= h($link['title']) ?></strong><br><code><?= h($link['id']) ?></code></td>
                <td><a href="<?= h($publicUrl) ?>"><?= h($publicUrl) ?></a><br><small><?= h($link['redirect_url']) ?></small></td>
                <td><?= (int) $link['clicks'] ?></td>
                <td class="actions">
                  <a class="button secondary" href="<?= h(current_url(['admin' => '1', 'edit' => $link['id']])) ?>">Sửa</a>
                  <form method="post" onsubmit="return confirm('Xóa link này?')">
                    <input type="hidden" name="delete_link" value="1">
                    <input type="hidden" name="id" value="<?= h($link['id']) ?>">
                    <button class="button danger" type="submit">Xóa</button>
                  </form>
                </td>
              </tr>
            <?php endforeach; ?>
            <?php if (!$links): ?><tr><td colspan="4">Chưa có link nào.</td></tr><?php endif; ?>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</body>
</html>
    <?php
}

function render_login(): void {
    ?>
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Đăng nhập</title>
  <style><?= base_css() ?></style>
</head>
<body class="public">
  <form method="post" class="verify-card login-card">
    <h1>Admin</h1>
    <p>Nhập mật khẩu quản trị để tạo/sửa link.</p>
    <input type="hidden" name="login" value="1">
    <label>Mật khẩu<input type="password" name="password" autofocus required></label>
    <button class="button" type="submit">Đăng nhập</button>
  </form>
</body>
</html>
    <?php
}

function base_css(): string {
    return <<<'CSS'
:root{color-scheme:light dark;--bg:#f1f5f9;--card:#fff;--ink:#0f172a;--muted:#64748b;--brand:#2563eb;--line:#dbe3ef;--danger:#dc2626}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.public{min-height:100vh;display:grid;place-items:center;padding:24px;background:linear-gradient(135deg,#dbeafe,#fff)}.verify-card{width:min(460px,100%);background:var(--card);border:1px solid var(--line);border-radius:28px;padding:32px;text-align:center;box-shadow:0 24px 70px rgba(15,23,42,.16)}.verify-card h1{margin:8px 0 10px;font-size:clamp(1.6rem,5vw,2.4rem)}.verify-card p{color:var(--muted);line-height:1.7}.eyebrow{font-size:.75rem;font-weight:900;letter-spacing:.18em;text-transform:uppercase}.loader{width:44px;height:44px;margin:0 auto 18px;border:4px solid #bfdbfe;border-top-color:var(--brand);border-radius:50%;animation:spin 1s linear infinite}.preview{width:100%;max-height:220px;object-fit:cover;border-radius:18px;border:1px solid var(--line);margin:10px 0}.safe-note{padding:12px;border-radius:14px;background:#ecfdf5;color:#047857!important;font-size:.9rem}.button{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:999px;background:var(--brand);color:#fff;padding:12px 18px;text-decoration:none;font-weight:800;cursor:pointer}.button.secondary{background:#e2e8f0;color:#0f172a}.button.danger{background:var(--danger)}.danger-link{color:#fca5a5;text-decoration:none;font-weight:700}.admin-layout{min-height:100vh;display:grid;grid-template-columns:260px 1fr}.sidebar{background:#0f172a;color:#e2e8f0;padding:28px;display:flex;flex-direction:column;gap:16px}.sidebar h1{margin:0}.sidebar p{color:#94a3b8}.admin-main{padding:28px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;align-content:start}.panel{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:22px;box-shadow:0 18px 45px rgba(15,23,42,.08)}.panel.full{grid-column:1/-1}.form-grid{display:grid;gap:12px}label{display:grid;gap:6px;color:var(--muted);font-size:.9rem;font-weight:700;text-align:left}input,textarea{width:100%;border:1px solid var(--line);border-radius:12px;padding:11px 12px;background:var(--card);color:var(--ink);font:inherit}textarea{resize:vertical}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:14px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}small,code{color:var(--muted)}.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.actions form{margin:0}@keyframes spin{to{transform:rotate(360deg)}}@media (max-width:850px){.admin-layout{grid-template-columns:1fr}.admin-main{grid-template-columns:1fr}.sidebar{position:static}}@media (prefers-color-scheme:dark){:root{--bg:#020617;--card:#0f172a;--ink:#e2e8f0;--muted:#94a3b8;--line:#1e293b}.public{background:linear-gradient(135deg,#0f172a,#020617)}.button.secondary{background:#1e293b;color:#e2e8f0}.safe-note{background:#052e16;color:#bbf7d0!important}}
CSS;
}
