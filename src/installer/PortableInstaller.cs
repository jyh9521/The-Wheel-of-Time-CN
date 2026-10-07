// Portable UI: no registry, installer service, shortcuts, or uninstall entry.
using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.Threading;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Collections.Generic;
using System.Web.Script.Serialization;

namespace LocalizationInstaller {
    static class Ui {
        static Dictionary<string,string> values = new Dictionary<string,string>();
        public static void Bootstrap() {
            using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("Package.zip"))
            using(var zip=new ZipArchive(stream,ZipArchiveMode.Read))
            using(var reader=new StreamReader(zip.GetEntry("LocalizationTest/UI.json").Open(),Encoding.UTF8))
                values=new JavaScriptSerializer().Deserialize<Dictionary<string,string>>(reader.ReadToEnd());
        }
        public static string Error(Exception ex) {
            string key=ex is ArgumentException || ex is NotSupportedException ? "path_invalid" :
                ex is UnauthorizedAccessException ? "error_access" : ex is DirectoryNotFoundException || ex is FileNotFoundException ? "missing_files" :
                ex is IOException ? "error_io" : "error_unknown";
            return T(key)+" ("+T("error_details")+": 0x"+ex.HResult.ToString("X8",CultureInfo.InvariantCulture)+")";
        }
        public static string BackendError(string output) {
            string key=output.Contains("Backup belongs to another package") ? "backup_package" :
                output.Contains("Unsupported original") || output.Contains("Unsupported game executable") ? "version_mismatch" :
                output.Contains("Read-only game file") ? "readonly_file" :
                output.Contains("No installation backup") ? "missing_backup" :
                output.Contains("External modification") || output.Contains("Changed addition") ? "external_change" :
                output.Contains("Package checksum differs") || output.Contains("Payload differs") ? "package_damaged" : "validation_failed";
            return T(key);
        }
        public static string BackendReport(string output) {
            var report = new StringBuilder(); var passed = new StringBuilder();
            foreach(string raw in output.Split(new char[] {'\r','\n'},StringSplitOptions.RemoveEmptyEntries)) {
                if(!raw.StartsWith("FILE_RESULT ",StringComparison.Ordinal)) continue;
                try {
                    var row=new JavaScriptSerializer().Deserialize<Dictionary<string,string>>(raw.Substring(12));
                    string reason=row["reason"];
                    string key="file_"+reason;
                    if(reason=="pass" || reason=="installed" || reason=="ready") { passed.Append(row["path"]).Append(": ").Append(T(key)).AppendLine(); continue; }
                    report.Append(row["path"]).Append(": ").Append(T(key)).AppendLine();
                    if(reason=="hash_mismatch") {
                        report.Append("  ").Append(T("expected_hash")).Append(": ").Append(row["expected"]).AppendLine();
                        report.Append("  ").Append(T("actual_hash")).Append(": ").Append(row["actual"]).AppendLine();
                    }
                    if(reason=="access" && row["actual"].StartsWith("0x")) report.Append("  ").Append(T("error_details")).Append(": ").Append(row["actual"]).AppendLine();
                } catch { report.AppendLine(T("report_invalid")); }
            }
            if(report.Length==0 && passed.Length==0) report.AppendLine(BackendError(output));
            return report.ToString()+passed.ToString();
        }
        public static void Load(string package) { values = new JavaScriptSerializer().Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(package, "LocalizationTest", "UI.json"), Encoding.UTF8)); }
        public static string T(string key) { return values.ContainsKey(key) ? values[key] : key; }
    }
    static class Program {
        public static string Extract() {
            using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("Package.zip")) {
                if (stream == null) throw new IOException(Ui.T("data_missing"));
                byte[] payload;
                using (var buffer = new MemoryStream()) { stream.CopyTo(buffer); payload = buffer.ToArray(); }
                string hash;
                using (var sha = SHA256.Create()) hash = BitConverter.ToString(sha.ComputeHash(payload)).Replace("-", "").ToLowerInvariant();
                string root = Path.Combine(Path.GetTempPath(), "LocalizationInstaller", hash);
                Directory.CreateDirectory(root);
                using (var zip = new ZipArchive(new MemoryStream(payload), ZipArchiveMode.Read)) {
                    foreach (var entry in zip.Entries) {
                        string path = Path.GetFullPath(Path.Combine(root, entry.FullName));
                        if (!path.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                            throw new IOException(Ui.T("data_path_invalid"));
                        Directory.CreateDirectory(Path.GetDirectoryName(path));
                        using (var input = entry.Open()) using (var output = new FileStream(path, FileMode.Create, FileAccess.Write)) input.CopyTo(output);
                    }
                }
                return root;
            }
        }
        public static string Quote(string arg) {
            if (arg.IndexOf('"') >= 0 || arg.IndexOf('\r') >= 0 || arg.IndexOf('\n') >= 0) throw new ArgumentException(Ui.T("path_invalid"));
            // Windows process quoting: double trailing backslashes before quote.
            int trailing = 0;
            for (int i = arg.Length - 1; i >= 0 && arg[i] == '\\'; i--) trailing++;
            return "\"" + arg + new string('\\', trailing) + "\"";
        }
        public static int Run(string package, string action, string game, out string output) {
            var start = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "WindowsPowerShell", "v1.0", "powershell.exe"));
            start.Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File " + Quote(Path.Combine(package, "LocalizationTest", "Manage-Patch.ps1")) + " -Action " + action + " -GameDir " + Quote(Path.GetFullPath(game));
            start.UseShellExecute = false; start.CreateNoWindow = true;
            start.RedirectStandardOutput = true; start.RedirectStandardError = true;
            start.StandardOutputEncoding = Encoding.UTF8; start.StandardErrorEncoding = Encoding.UTF8;
            using (var process = Process.Start(start)) {
                Task<string> stdout = process.StandardOutput.ReadToEndAsync();
                Task<string> stderr = process.StandardError.ReadToEndAsync();
                process.WaitForExit(); Task.WaitAll(stdout, stderr);
                output = stdout.Result + stderr.Result;
                return process.ExitCode;
            }
        }
        [STAThread] static int Main(string[] args) {
            Thread.CurrentThread.CurrentCulture = CultureInfo.GetCultureInfo("zh-CN");
            Thread.CurrentThread.CurrentUICulture = CultureInfo.GetCultureInfo("zh-CN");
            try {
                Ui.Bootstrap();
                string package = Extract(); Ui.Load(package);
                if (args.Length == 4 && args[0] == "--headless") {
                    if (args[1] != "check" && args[1] != "apply" && args[1] != "verify" && args[1] != "restore") throw new ArgumentException("Invalid test action");
                    string output; int result = Run(package, args[1], args[2], out output);
                    File.WriteAllText(args[3], output, new UTF8Encoding(false));
                    return result;
                }
                Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
                if(args.Length==4 && args[0]=="--ui-check-smoke") {
                    Thread.CurrentThread.CurrentUICulture=CultureInfo.GetCultureInfo(args[3]);
                    using(var form=new InstallerForm(package)) { form.Show(); Application.DoEvents(); form.ProbeCheck(args[2]);
                        using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(0,0,bitmap.Width,bitmap.Height));bitmap.Save(args[1]);} form.Close(); } return 0;
                }
                if ((args.Length == 2 && args[0] == "--ui-smoke") || (args.Length == 3 && args[0] == "--ui-error-smoke")) {
                    if(args.Length==3) { Thread.CurrentThread.CurrentCulture=CultureInfo.GetCultureInfo(args[2]); Thread.CurrentThread.CurrentUICulture=CultureInfo.GetCultureInfo(args[2]); }
                    using (var form = new InstallerForm(package)) {
                        form.Show(); Application.DoEvents();
                        if(args[0]=="--ui-error-smoke") form.ProbeInvalidPath();
                        using (var bitmap = new Bitmap(form.Width, form.Height)) {
                            form.DrawToBitmap(bitmap, new Rectangle(0, 0, bitmap.Width, bitmap.Height)); bitmap.Save(args[1]);
                        }
                        form.Close();
                    }
                    return 0;
                }
                Application.Run(new InstallerForm(package)); return 0;
            } catch (Exception ex) { if (args.Length == 0) DialogUi.Notify(Ui.T("message_title"), Ui.Error(ex)); return 1; }
        }
    }
    static class Theme {
        public static readonly Color Surface = Color.FromArgb(248, 247, 252);
        public static readonly Color Primary = Color.FromArgb(88, 68, 146);
        public static readonly Color Ink = Color.FromArgb(30, 27, 36);
        public static GraphicsPath Shape(RectangleF rect, float radius) {
            var p = new GraphicsPath(); float d = radius * 2;
            p.AddArc(rect.X, rect.Y, d, d, 180, 90);
            p.AddArc(rect.Right-d, rect.Y, d, d, 270, 90);
            p.AddArc(rect.Right-d, rect.Bottom-d, d, d, 0, 90);
            p.AddArc(rect.X, rect.Bottom-d, d, d, 90, 90); p.CloseFigure(); return p;
        }
    }
    sealed class SurfacePanel : Panel {
        public SurfacePanel() { DoubleBuffered = true; BackColor = Theme.Surface; }
        protected override void OnPaintBackground(PaintEventArgs e) {
            base.OnPaintBackground(e);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            using(var shape=Theme.Shape(new RectangleF(0,0,Width-1,Height-1),16))
            using(var brush=new SolidBrush(SystemInformation.HighContrast ? SystemColors.Window : Color.White)) e.Graphics.FillPath(brush,shape);
        }
    }
    sealed class MaterialButton : Button {
        public bool Primary;
        bool hovered, pressed;
        public MaterialButton() { FlatStyle=FlatStyle.Flat; FlatAppearance.BorderSize=0; Cursor=Cursors.Hand; SetStyle(ControlStyles.OptimizedDoubleBuffer|ControlStyles.UserPaint, true); }
        protected override void OnMouseEnter(EventArgs e) { hovered=true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { hovered=false; pressed=false; Invalidate(); base.OnMouseLeave(e); }
        protected override void OnMouseDown(MouseEventArgs e) { pressed=true; Invalidate(); base.OnMouseDown(e); }
        protected override void OnMouseUp(MouseEventArgs e) { pressed=false; Invalidate(); base.OnMouseUp(e); }
        protected override void OnPaint(PaintEventArgs e) {
            if(SystemInformation.HighContrast) { base.OnPaint(e); return; }
            e.Graphics.Clear(Parent is SurfacePanel ? Color.White : Parent.BackColor); e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
            Color fill=!Enabled ? Color.FromArgb(233,230,238) : Primary ? Theme.Primary : Color.FromArgb(238,232,249);
            if(Enabled && (hovered || pressed)) fill=ControlPaint.Dark(fill, pressed ? 0.10f : 0.04f);
            using(var shape=Theme.Shape(new RectangleF(1,1,Width-3,Height-3),Math.Min(22,(Height-3)/2)))
            using(var brush=new SolidBrush(fill)) e.Graphics.FillPath(brush,shape);
            TextRenderer.DrawText(e.Graphics,Text,Font,ClientRectangle,!Enabled ? Color.FromArgb(130,125,139) : Primary ? Color.White : Theme.Primary,TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter);
            if(Focused && ShowFocusCues) ControlPaint.DrawFocusRectangle(e.Graphics,Rectangle.Inflate(ClientRectangle,-7,-7));
        }
    }
    static class DialogUi {
        public static bool Confirm(IWin32Window owner,string title,string message) {
            using(var form=Create(title,message,true)) return form.ShowDialog(owner)==DialogResult.OK;
        }
        public static void Notify(string title,string message) { using(var form=Create(title,message,false)) form.ShowDialog(); }
        static Form Create(string title,string message,bool cancel) {
            var form=new Form { Text=title, Font=new Font(Ui.T("font_family"),10), ClientSize=new Size(520,180), FormBorderStyle=FormBorderStyle.FixedDialog, MaximizeBox=false, MinimizeBox=false, StartPosition=FormStartPosition.CenterParent, BackColor=Theme.Surface };
            var text=new Label { Text=message, Bounds=new Rectangle(24,24,472,80) };
            var ok=new MaterialButton { Text=Ui.T("confirm"), Primary=true, DialogResult=DialogResult.OK, Bounds=new Rectangle(356,118,140,42) };
            form.Controls.AddRange(new Control[]{text,ok}); form.AcceptButton=ok;
            if(cancel) { var no=new MaterialButton { Text=Ui.T("cancel"), DialogResult=DialogResult.Cancel, Bounds=new Rectangle(204,118,140,42) }; form.Controls.Add(no); form.CancelButton=no; }
            return form;
        }
    }
    sealed class DirectoryPicker : Form {
        readonly TreeView tree=new TreeView(); readonly TextBox path=new TextBox(); readonly Label info=new Label();
        public string SelectedPath { get { return path.Text; } }
        public DirectoryPicker(string initial) {
            Text=Ui.T("directory_title_picker"); Font=new Font(Ui.T("font_family"),10); ClientSize=new Size(640,450);
            AutoScaleMode=AutoScaleMode.Font; BackColor=Theme.Surface; StartPosition=FormStartPosition.CenterParent;
            FormBorderStyle=FormBorderStyle.FixedDialog; MaximizeBox=false; MinimizeBox=false;
            path.ContextMenuStrip = new ContextMenuStrip(); path.SetBounds(20,20,600,30); path.Text=initial;
            tree.SetBounds(20,64,600,275); info.SetBounds(20,348,600,35);
            var ok=new MaterialButton { Text=Ui.T("confirm"), Primary=true, Bounds=new Rectangle(480,394,140,40) };
            var cancel=new MaterialButton { Text=Ui.T("cancel"), DialogResult=DialogResult.Cancel, Bounds=new Rectangle(328,394,140,40) };
            foreach(string drive in Directory.GetLogicalDrives()) Add(tree.Nodes,drive,drive);
            tree.BeforeExpand += delegate(object sender,TreeViewCancelEventArgs e) {
                if(e.Node.Nodes.Count!=1 || e.Node.Nodes[0].Tag!=null) return;
                e.Node.Nodes.Clear();
                try { foreach(string dir in Directory.GetDirectories((string)e.Node.Tag)) Add(e.Node.Nodes,Path.GetFileName(dir),dir); }
                catch(Exception ex) { info.Text=Ui.Error(ex); }
            };
            tree.AfterSelect += delegate(object sender,TreeViewEventArgs e) { if(e.Node.Tag!=null) path.Text=(string)e.Node.Tag; };
            ok.Click += delegate {
                try { if(String.IsNullOrWhiteSpace(path.Text)) throw new ArgumentException(); string full=Path.GetFullPath(path.Text.Trim());
                    if(!Directory.Exists(full)) { info.Text=Ui.T("directory_missing"); return; }
                    path.Text=full; DialogResult=DialogResult.OK; Close();
                } catch(Exception ex) { info.Text=Ui.Error(ex); }
            };
            Controls.AddRange(new Control[]{path,tree,info,ok,cancel}); AcceptButton=ok; CancelButton=cancel;
        }
        static void Add(TreeNodeCollection nodes,string label,string full) { var n=nodes.Add(label); n.Tag=full; n.Nodes.Add("..."); }
    }
    sealed class InstallerForm : Form {
        readonly string package;
        readonly TextBox folder = new TextBox();
        readonly TextBox log = new TextBox();
        readonly MaterialButton browse = new MaterialButton(), check = new MaterialButton(), install = new MaterialButton { Primary = true }, restore = new MaterialButton();
        readonly ProgressBar progress = new ProgressBar();
        readonly Label status = new Label();
        bool busy;
        string checkedPath;
        public InstallerForm(string data) {
            package = data; Text = Ui.T("window_title");
            Font = new Font(Ui.T("font_family"), 10); AutoScaleMode = AutoScaleMode.Font;
            ClientSize = new Size(780, 632); BackColor = SystemInformation.HighContrast ? SystemColors.Control : Theme.Surface;
            ForeColor = SystemInformation.HighContrast ? SystemColors.ControlText : Theme.Ink;
            FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false; StartPosition = FormStartPosition.CenterScreen;
            var heading = new Label { Text = Ui.T("window_title"), Font = new Font(Font.FontFamily,18,FontStyle.Bold), AutoSize = false, Bounds = new Rectangle(24,20,732,38) };
            var title = new Label { Text = Ui.T("instruction"), AutoSize = false, Bounds = new Rectangle(24,66,732,40) };
            var directoryCard = new SurfacePanel { Bounds = new Rectangle(24,116,732,100) };
            var directoryLabel = new Label { Text = Ui.T("directory_title"), AutoSize = true, Location = new Point(18,12), BackColor = SystemInformation.HighContrast ? SystemColors.Window : Color.White };
            folder.ContextMenuStrip = new ContextMenuStrip(); log.ContextMenuStrip = new ContextMenuStrip();
            folder.SetBounds(18,43,568,30); folder.BorderStyle = BorderStyle.FixedSingle;
            browse.Text = Ui.T("browse"); browse.SetBounds(598,35,116,44);
            directoryCard.Controls.AddRange(new Control[] { directoryLabel, folder, browse });
            check.Text = Ui.T("check"); check.SetBounds(24,232,140,44);
            install.Text = Ui.T("install"); install.SetBounds(176,232,176,44); install.Enabled = false;
            restore.Text = Ui.T("restore"); restore.SetBounds(616,232,140,44);
            status.SetBounds(24,290,732,36); status.Text = Ui.T("choose_prompt");
            progress.SetBounds(24,329,732,6); progress.Style = ProgressBarStyle.Marquee; progress.Visible = false;
            var logCard = new SurfacePanel { Bounds = new Rectangle(24,349,732,137) };
            var logTitle = new Label { Text = Ui.T("log_title"), AutoSize = true, Location = new Point(18,12), BackColor = SystemInformation.HighContrast ? SystemColors.Window : Color.White };
            log.SetBounds(18,38,696,82); log.Multiline = true; log.ReadOnly = true; log.ScrollBars = ScrollBars.Vertical;
            log.BorderStyle = BorderStyle.None; log.BackColor = SystemInformation.HighContrast ? SystemColors.Window : Color.White;
            logCard.Controls.AddRange(new Control[] { logTitle, log });
            var note = new Label { Text = Ui.T("footnote"), AutoSize = false, Bounds = new Rectangle(24,504,732,84), ForeColor = SystemInformation.HighContrast ? SystemColors.ControlText : Color.FromArgb(91,85,102) };
            var attribution = new LinkLabel { Text = Ui.T("attribution_text"), AutoSize = false,
                Bounds = new Rectangle(24,600,732,24), TextAlign = ContentAlignment.MiddleRight,
                Anchor = AnchorStyles.Bottom | AnchorStyles.Right,
                LinkColor = SystemInformation.HighContrast ? SystemColors.HotTrack : Color.FromArgb(103,80,164),
                LinkBehavior = LinkBehavior.HoverUnderline, AccessibleName = Ui.T("attribution_text") };
            attribution.LinkClicked += delegate {
                try { var url = new Uri(Ui.T("attribution_url"));
                    if(url.Scheme != Uri.UriSchemeHttps) throw new ArgumentException();
                    Process.Start(new ProcessStartInfo(url.AbsoluteUri) { UseShellExecute = true });
                } catch(Exception ex) { status.Text=Ui.Error(ex); }
            };
            Controls.AddRange(new Control[] { heading, title, directoryCard, check, install, restore, status, progress, logCard, note, attribution });
            AcceptButton = check;
            folder.TextChanged += delegate { checkedPath = null; install.Enabled = false; AcceptButton = check; };
            browse.Click += delegate { using (var picker = new DirectoryPicker(folder.Text)) if (picker.ShowDialog(this) == DialogResult.OK) folder.Text = picker.SelectedPath; };
            check.Click += async delegate { await Execute("check"); };
            install.Click += async delegate { await Execute("apply"); };
            restore.Click += async delegate {
                if (DialogUi.Confirm(this, Ui.T("restore"), Ui.T("restore_confirmation"))) await Execute("restore");
            };
            FormClosing += delegate(object sender, FormClosingEventArgs e) { if (busy) { e.Cancel = true; status.Text = Ui.T("busy_close"); } };
        }
        public void ProbeCheck(string game) {
            folder.Text=game; string output; int exit=Program.Run(package,"check",game,out output);
            log.AppendText(Ui.BackendReport(output)); log.SelectionStart=0; log.SelectionLength=0; log.ScrollToCaret(); status.Text=exit==0 ? Ui.T("check_complete") : Ui.BackendError(output);
            if(!log.Text.Contains("System/")) throw new InvalidOperationException("File report probe failed");
        }
        public void ProbeInvalidPath() {
            folder.Text=""; check.PerformClick();
            if(!status.Text.StartsWith(Ui.T("path_invalid"),StringComparison.Ordinal)) throw new InvalidOperationException("Invalid path probe failed");
        }
        async Task Execute(string action) {
            string game;
            try { if(String.IsNullOrWhiteSpace(folder.Text)) throw new ArgumentException(); game = Path.GetFullPath(folder.Text.Trim()); if (!Directory.Exists(game)) throw new IOException(Ui.T("directory_missing")); }
            catch (Exception ex) { status.Text = Ui.Error(ex); log.AppendText(status.Text + Environment.NewLine); return; }
            if (action == "apply" && checkedPath != game) { status.Text = Ui.T("check_required"); return; }
            busy = true; browse.Enabled = check.Enabled = install.Enabled = restore.Enabled = folder.Enabled = false;
            progress.Visible = true; status.Text = action == "check" ? Ui.T("checking") : action == "apply" ? Ui.T("installing") : Ui.T("restoring");
            log.AppendText(status.Text + Environment.NewLine);
            try {
                string result = ""; int exit = await Task.Run(() => Program.Run(package, action, game, out result));
                if (action == "check" || exit != 0) { int reportStart=log.TextLength; log.AppendText(Ui.BackendReport(result)); log.SelectionStart=reportStart; log.SelectionLength=0; log.ScrollToCaret(); }
                if (exit != 0) { checkedPath = null; status.Text = Ui.T("validation_failed");
                    status.Text = Ui.BackendError(result);
                }
                else if (action == "check") { checkedPath = game; status.Text = Ui.T("check_complete"); log.AppendText(Ui.T("check_log_complete") + Environment.NewLine + status.Text + Environment.NewLine); }
                else if (action == "apply") {
                    string verified = ""; int verifyExit = await Task.Run(() => Program.Run(package, "verify", game, out verified));
                    if (verifyExit != 0) log.AppendText(Ui.BackendReport(verified)); if (verifyExit != 0) throw new IOException(Ui.T("verify_failed"));
                    checkedPath = null; status.Text = Ui.T("install_complete"); log.AppendText(Ui.T("backup_complete") + Environment.NewLine + Ui.T("install_log_complete") + Environment.NewLine);
                } else { checkedPath = null; status.Text = Ui.T("restore_complete"); log.AppendText(status.Text + Environment.NewLine); }
            } catch (Exception ex) { checkedPath = null; log.AppendText(Ui.Error(ex)); status.Text = Ui.Error(ex); }
            finally { busy = false; browse.Enabled = check.Enabled = restore.Enabled = folder.Enabled = true; install.Enabled = checkedPath == game; AcceptButton = install.Enabled ? (IButtonControl)install : check; progress.Visible = false; }
        }
    }
}
