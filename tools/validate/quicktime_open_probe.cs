// 32-bit, read-only QuickTime movie opening probe. No game/window/playback.
using System;
using System.Runtime.InteropServices;
using System.Text;

public class QuickTimeOpenProbe {
    const string QT = "QTMLClient.dll";
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern bool SetDllDirectory(string path);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short InitializeQTML(int flags);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short EnterMovies();
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void ExitMovies();
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void TerminateQTML();
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short FSMakeFSSpec(short volume, int directory, byte[] name, byte[] spec);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short OpenMovieFile(byte[] spec, out short reference, sbyte permission);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short NewMovieFromFile(out IntPtr movie, short reference, IntPtr resourceId, IntPtr resourceName, short flags, IntPtr changed);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern short CloseMovieFile(short reference);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern void DisposeMovie(IntPtr movie);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern int GetMovieTrackCount(IntPtr movie);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern IntPtr GetMovieIndTrackType(IntPtr movie, int ordinal, uint type, int flags);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern int GetTrackID(IntPtr track);
    [DllImport(QT, CallingConvention=CallingConvention.Cdecl)] static extern byte GetTrackEnabled(IntPtr track);

    public static int Main(string[] args) {
        if (args.Length != 2 || IntPtr.Size != 4) { Console.Error.WriteLine("Usage: x86 probe.exe QTSystem movie.mov"); return 2; }
        SetDllDirectory(args[0]);
        IntPtr movie = IntPtr.Zero;
        bool initialized = false, entered = false, opened = false;
        short reference = 0;
        try {
            short err = InitializeQTML(0);
            if (err != 0) throw new Exception("InitializeQTML=" + err);
            initialized = true;
            err = EnterMovies();
            if (err != 0) throw new Exception("EnterMovies=" + err);
            entered = true;
            byte[] name = Encoding.Default.GetBytes(System.IO.Path.GetFullPath(args[1]));
            if (name.Length > 255) throw new Exception("Path exceeds Pascal string limit");
            byte[] pascal = new byte[name.Length + 1];
            pascal[0] = (byte)name.Length; Array.Copy(name, 0, pascal, 1, name.Length);
            byte[] spec = new byte[70];
            err = FSMakeFSSpec(0, 0, pascal, spec);
            if (err != 0) throw new Exception("FSMakeFSSpec=" + err);
            err = OpenMovieFile(spec, out reference, 1);
            if (err != 0) throw new Exception("OpenMovieFile=" + err);
            opened = true;
            err = NewMovieFromFile(out movie, reference, IntPtr.Zero, IntPtr.Zero, 1, IntPtr.Zero);
            if (err != 0 || movie == IntPtr.Zero) throw new Exception("NewMovieFromFile=" + err);
            Console.Write("QUICKTIME OPEN PASS: tracks=" + GetMovieTrackCount(movie) + "; text=");
            for (int i=1; ; i++) {
                IntPtr track = GetMovieIndTrackType(movie, i, 0x74657874, 1);
                if (track == IntPtr.Zero) break;
                Console.Write((i == 1 ? "" : ",") + GetTrackID(track) + ":enabled=" + GetTrackEnabled(track));
            }
            Console.WriteLine("; rendering=NOT_TESTED");
            return 0;
        } catch (Exception ex) { Console.Error.WriteLine(ex.Message); return 1; }
        finally {
            if (movie != IntPtr.Zero) DisposeMovie(movie);
            if (opened) CloseMovieFile(reference);
            if (entered) ExitMovies();
            if (initialized) TerminateQTML();
        }
    }
}
