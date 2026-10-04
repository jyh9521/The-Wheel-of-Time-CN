// Independent native QuickTime test player. Original files remain read-only.
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

public sealed class NativeMovie : IDisposable {
    const string QT = "QTMLClient.dll";
    [StructLayout(LayoutKind.Sequential, Pack=2)] public struct QTRect { public short top,left,bottom,right; }
    [StructLayout(LayoutKind.Sequential, Pack=2)] public struct RGBColor { public ushort red,green,blue; }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern bool SetDllDirectory(string path);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short InitializeQTML(int flags);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short EnterMovies();
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void ExitMovies();
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void TerminateQTML();
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short FSMakeFSSpec(short v,int d,byte[] name,byte[] spec);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short OpenMovieFile(byte[] spec,out short reference,sbyte permission);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short CloseMovieFile(short reference);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short NewMovieFromFile(out IntPtr movie,short reference,IntPtr id,IntPtr name,short flags,IntPtr changed);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void DisposeMovie(IntPtr movie);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern IntPtr GetMovieIndTrackType(IntPtr movie,int ordinal,uint type,int flags);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void SetTrackEnabled(IntPtr track,byte enabled);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void SetAutoTrackAlternatesEnabled(IntPtr movie,byte enabled);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void SetTrackMatrix(IntPtr track,int[] matrix);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void GetMovieBox(IntPtr movie,out QTRect box);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void SetMovieBox(IntPtr movie,ref QTRect box);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short QTNewGWorldFromPtr(out IntPtr world,uint format,ref QTRect bounds,IntPtr colors,IntPtr device,uint flags,IntPtr pixels,int rowBytes);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void DisposeGWorld(IntPtr world);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void SetGWorld(IntPtr world,IntPtr device);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void RGBBackColor(ref RGBColor color);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void SetMovieGWorld(IntPtr movie,IntPtr world,IntPtr device);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void MoviesTask(IntPtr movie,int milliseconds);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short UpdateMovie(IntPtr movie);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern int GetMovieTimeScale(IntPtr movie);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern int GetMovieDuration(IntPtr movie);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void SetMovieVolume(IntPtr movie,short volume);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern int GetMovieTime(IntPtr movie,IntPtr record);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void SetMovieTimeValue(IntPtr movie,int value);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void StartMovie(IntPtr movie);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void StopMovie(IntPtr movie);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern byte IsMovieDone(IntPtr movie);

    public const int Width=1920, Height=1080;
    IntPtr movie=IntPtr.Zero, world=IntPtr.Zero, pixels=IntPtr.Zero;
    bool initialized,entered;
    readonly byte[] buffer=new byte[Width*Height*4];
    public readonly Bitmap Frame=new Bitmap(Width,Height,PixelFormat.Format32bppArgb);
    public bool Captions { get; private set; }
    public double Seconds { get { return (double)GetMovieTime(movie,IntPtr.Zero)/GetMovieTimeScale(movie); } }
    public double Duration { get { return (double)GetMovieDuration(movie)/GetMovieTimeScale(movie); } }
    public bool Done { get { return IsMovieDone(movie)!=0; } }

    static void Check(short error,string operation) { if(error!=0) throw new Exception(operation+"="+error); }
    public NativeMovie(string runtime,string file,bool captions) {
        try {
            if(IntPtr.Size!=4) throw new Exception("32-bit executable required");
            if(!File.Exists(Path.Combine(runtime,QT)) || !File.Exists(file)) throw new Exception("Runtime/movie missing");
            SetDllDirectory(Path.GetFullPath(runtime));
            Check(InitializeQTML(0),"InitializeQTML"); initialized=true;
            Check(EnterMovies(),"EnterMovies"); entered=true;
            byte[] name=Encoding.Default.GetBytes(Path.GetFullPath(file));
            if(name.Length>255 || Encoding.Default.GetString(name)!=Path.GetFullPath(file)) throw new Exception("Movie path is not representable by native ANSI API");
            byte[] pascal=new byte[name.Length+1]; pascal[0]=(byte)name.Length;
            Array.Copy(name,0,pascal,1,name.Length);
            byte[] spec=new byte[70];
            Check(FSMakeFSSpec(0,0,pascal,spec),"FSMakeFSSpec");
            short reference; Check(OpenMovieFile(spec,out reference,1),"OpenMovieFile");
            try { Check(NewMovieFromFile(out movie,reference,IntPtr.Zero,IntPtr.Zero,1,IntPtr.Zero),"NewMovieFromFile"); }
            finally { CloseMovieFile(reference); }
            if(movie==IntPtr.Zero) throw new Exception("Empty movie");
            SetAutoTrackAlternatesEnabled(movie,0);
            // Keep the first (English) sound track; subtitle selection is separate.
            for(int i=1;;i++) {
                IntPtr track=GetMovieIndTrackType(movie,i,0x736f756e,1);
                if(track==IntPtr.Zero) break;
                SetTrackEnabled(track,(byte)(i==1?1:0));
            }
            SetCaptions(false);
            QTRect original; GetMovieBox(movie,out original);
            int w=original.right-original.left,h=original.bottom-original.top;
            if(w<=0||h<=0) throw new Exception("Invalid movie bounds");
            // Match the game's below-video text-track placement, without changing the file.
            for(int i=1;;i++) {
                IntPtr track=GetMovieIndTrackType(movie,i,0x74657874,1);
                if(track==IntPtr.Zero) break;
                SetTrackMatrix(track,new int[] {65536,0,0,0,65536,0,0,h*65536,0x40000000});
            }
            SetCaptions(true);
            GetMovieBox(movie,out original);
            w=original.right-original.left;h=original.bottom-original.top;
            Console.WriteLine("NATIVE BOUNDS: "+w+"x"+h+"; target=1920x1080; audio=first; captions="+(captions?"on":"off"));
            QTRect bounds=new QTRect { right=Width,bottom=Height };
            pixels=Marshal.AllocHGlobal(buffer.Length);
            for(int i=0;i<buffer.Length;i+=4) buffer[i]=255;
            Marshal.Copy(buffer,0,pixels,buffer.Length);
            // k32ARGBPixelFormat: byte order A,R,G,B, converted only for the preview bitmap.
            Check(QTNewGWorldFromPtr(out world,32,ref bounds,IntPtr.Zero,IntPtr.Zero,0,pixels,Width*4),"QTNewGWorldFromPtr");
            SetGWorld(world,IntPtr.Zero);
            RGBColor black=new RGBColor();RGBBackColor(ref black);
            SetMovieGWorld(movie,world,IntPtr.Zero);
            double scale=Math.Min((double)Width/w,(double)Height/h);
            int rw=(int)Math.Round(w*scale),rh=(int)Math.Round(h*scale);
            QTRect box=new QTRect { left=(short)((Width-rw)/2),top=(short)((Height-rh)/2),right=(short)((Width+rw)/2),bottom=(short)((Height+rh)/2) };
            SetMovieBox(movie,ref box);
            SetCaptions(captions);
        } catch { Dispose(); throw; }
    }
    public void SetCaptions(bool enabled) {
        for(int i=1;;i++) {
            IntPtr track=GetMovieIndTrackType(movie,i,0x74657874,1);
            if(track==IntPtr.Zero) break;
            SetTrackEnabled(track,(byte)(enabled&&i==1?1:0));
        }
        Captions=enabled;
    }
    public void Seek(double seconds) { Stop(); SetMovieTimeValue(movie,(int)(seconds*GetMovieTimeScale(movie))); Draw(); }
    public void Start() { StartMovie(movie); }
    public void MuteForTest() { SetMovieVolume(movie,0); }
    public void Stop() { if(movie!=IntPtr.Zero) StopMovie(movie); }
    public void Draw() {
        MoviesTask(movie,0); Check(UpdateMovie(movie),"UpdateMovie");
        Marshal.Copy(pixels,buffer,0,buffer.Length);
        for(int i=0;i<buffer.Length;i+=4) { byte r=buffer[i+1],b=buffer[i+3]; buffer[i]=b;buffer[i+1]=buffer[i+2];buffer[i+2]=r;buffer[i+3]=255; }
        BitmapData dest=Frame.LockBits(new Rectangle(0,0,Width,Height),ImageLockMode.WriteOnly,PixelFormat.Format32bppArgb);
        try { Marshal.Copy(buffer,0,dest.Scan0,buffer.Length); }
        finally { Frame.UnlockBits(dest); }
    }
    public void Dispose() {
        Stop();
        if(movie!=IntPtr.Zero) { DisposeMovie(movie);movie=IntPtr.Zero; }
        if(world!=IntPtr.Zero) { DisposeGWorld(world);world=IntPtr.Zero; }
        if(pixels!=IntPtr.Zero) { Marshal.FreeHGlobal(pixels);pixels=IntPtr.Zero; }
        Frame.Dispose();
        if(entered) { ExitMovies();entered=false; }
        if(initialized) { TerminateQTML();initialized=false; }
    }
}

public sealed class MoviePreviewForm : Form {
    readonly NativeMovie movie;
    readonly Timer timer=new Timer();
    bool playing=true;
    public MoviePreviewForm(NativeMovie source) {
        movie=source; Text="FMV subtitle preview | Space: pause | R: replay | C: captions | Esc: exit";
        AutoScaleMode=AutoScaleMode.None;
        ClientSize=new Size(1920,1080); BackColor=Color.Black; KeyPreview=true; DoubleBuffered=true;
        timer.Interval=33;
        timer.Tick+=delegate { try { movie.Draw(); Invalidate(); if(movie.Done) { movie.Stop();playing=false; } } catch(Exception ex) { timer.Stop();movie.Stop();MessageBox.Show(ex.Message); } };
        Shown+=delegate { movie.Seek(0);movie.Start();timer.Start(); };
        FormClosing+=delegate { timer.Stop();movie.Stop(); };
        KeyDown+=delegate(object sender,KeyEventArgs e) {
            if(e.KeyCode==Keys.Escape) Close();
            if(e.KeyCode==Keys.Space) { if(playing) movie.Stop();else movie.Start(); playing=!playing; }
            if(e.KeyCode==Keys.R) { movie.Seek(0);movie.Start();playing=true; }
            if(e.KeyCode==Keys.C) { movie.SetCaptions(!movie.Captions);movie.Draw();Invalidate(); }
        };
    }
    protected override void OnPaint(PaintEventArgs e) {
        base.OnPaint(e);
        double scale=Math.Min((double)ClientSize.Width/1920,(double)ClientSize.Height/1080);
        int w=(int)(1920*scale),h=(int)(1080*scale);
        e.Graphics.DrawImage(movie.Frame,new Rectangle((ClientSize.Width-w)/2,(ClientSize.Height-h)/2,w,h));
    }
    protected override void Dispose(bool disposing) { if(disposing) timer.Dispose();base.Dispose(disposing); }
}

public static class QuickTimePlayer {
    static int CaptionInk(Bitmap frame) {
        int count=0;
        for(int y=1037;y<1080;y++) for(int x=0;x<1920;x++) {
            Color c=frame.GetPixel(x,y);
            if(c.R>100 || c.G>100 || c.B>100) count++;
        }
        return count;
    }
    [STAThread] public static int Main(string[] args) {
        try {
            if(args.Length<4 || (args[0]!="render" && args[0]!="play" && args[0]!="transitions" && args[0]!="timing")) throw new Exception("Usage: player.exe render|play|transitions|timing QTSystem movie on|off [output.png seconds]");
            if(args[3]!="on" && args[3]!="off") throw new Exception("Caption mode must be on/off");
            using(NativeMovie movie=new NativeMovie(args[1],args[2],args[3]=="on")) {
                if(args[0]=="timing") {
                    movie.MuteForTest();movie.Seek(2);movie.Start();
                    var watch=System.Diagnostics.Stopwatch.StartNew();
                    while(watch.ElapsedMilliseconds<700) { Application.DoEvents();movie.Draw();System.Threading.Thread.Sleep(5); }
                    movie.Stop();double stopped=movie.Seconds;
                    System.Threading.Thread.Sleep(150);movie.Draw();
                    Console.WriteLine("TIMING CLOCK: stopped="+stopped.ToString("F3",System.Globalization.CultureInfo.InvariantCulture)+"; paused="+movie.Seconds.ToString("F3",System.Globalization.CultureInfo.InvariantCulture));
                    if(stopped<2.1 || Math.Abs(movie.Seconds-stopped)>0.02) throw new Exception("Start/pause clock mismatch");
                    movie.Seek(0);if(movie.Seconds>0.01) throw new Exception("Replay seek mismatch");
                    movie.Seek(Math.Max(0,movie.Duration-0.15));movie.Start();watch.Restart();
                    while(!movie.Done && watch.ElapsedMilliseconds<2000) { movie.Draw();System.Threading.Thread.Sleep(5); }
                    movie.Stop();if(!movie.Done) throw new Exception("End-of-movie mismatch");
                    Console.WriteLine("NATIVE TIMING PASS: start/pause/replay/end; audio=muted-test-only");
                } else if(args[0]=="transitions") {
                    if(args.Length!=5) throw new Exception("Transitions needs a new PNG prefix");
                    string[] paths={args[4]+".on.png",args[4]+".off.png",args[4]+".replay.png",args[4]+".blank.png"};
                    foreach(string path in paths) if(File.Exists(path)) throw new Exception("Output exists: "+path);
                    movie.SetCaptions(true);movie.Seek(2);movie.Frame.Save(paths[0]);int on=CaptionInk(movie.Frame);
                    movie.SetCaptions(false);movie.Draw();movie.Frame.Save(paths[1]);int off=CaptionInk(movie.Frame);
                    movie.SetCaptions(true);movie.Seek(2);movie.Frame.Save(paths[2]);int replay=CaptionInk(movie.Frame);
                    movie.Seek(0.5);movie.Frame.Save(paths[3]);int blank=CaptionInk(movie.Frame);
                    Console.WriteLine("TRANSITIONS: on="+on+"; off="+off+"; replay="+replay+"; blank="+blank);
                    if(on==0 || off!=0 || replay!=on || blank!=0) throw new Exception("Caption transition mismatch");
                    Console.WriteLine("NATIVE TRANSITIONS PASS: on/off/replay/blank");
                } else if(args[0]=="render") {
                    if(args.Length!=6 || File.Exists(args[4])) throw new Exception("Render needs a new PNG path and time");
                    movie.Seek(double.Parse(args[5],System.Globalization.CultureInfo.InvariantCulture));
                    movie.Frame.Save(args[4],ImageFormat.Png);
                    Console.WriteLine("NATIVE RENDER PASS: 1920x1080; seconds="+args[5]+"; captions="+args[3]);
                } else {
                    Application.EnableVisualStyles();
                    using(MoviePreviewForm form=new MoviePreviewForm(movie)) Application.Run(form);
                    Console.WriteLine("NATIVE PLAY CLOSED: captions="+(movie.Captions?"on":"off"));
                }
            }
            return 0;
        } catch(Exception ex) { Console.Error.WriteLine(ex.Message);return 1; }
    }
}
