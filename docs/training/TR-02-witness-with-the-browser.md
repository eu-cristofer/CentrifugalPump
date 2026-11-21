# TR-02 · Witnessing with the browser version

**Goal.** By the end you can set up the browser version once, run a witness session with
no network, and export the reports.  The checks themselves (which tolerance applies, what
to ask) are in [TR-01](TR-01-witness-performance-test.md); the browser gives the same
verdicts as the desktop workbench.

---

## 1 · Install once, at the office

1. Open the PumpFlow web address while you are online.
2. Wait until the top bar says **Ready offline**.  The browser is saving the app and the
   Python engine (about 30 MB).
3. Optional: use the browser's **Install app** to open PumpFlow in its own window.
4. Test it: turn the network off, reload the page, and open a project.  If the page
   loads, you are ready.

Use the same browser and the same profile at the bench.  Do not clear the site data.

## 2 · At the bench

1. Open PumpFlow.  No network is needed.
2. Click **Open** and choose the `.pumpflow` project (or drop the file on the page).
3. Double-click a node to fill it in.  The form opens in a side panel.
   - **Test Points:** type or paste the rows.  Head and efficiency update as you type.
   - **MRT Log:** use **Add reading** for each new reading.
   - **NPSH:** enter the test values.
4. Read the pills on the nodes: green for pass, red for fail, amber for provisional or
   not fully assessed.  Open **Compliance** and **MRT Check** for the rows behind a pill.
5. If the vendor and the purchaser agree on a different tolerance, use **Override
   acceptance criteria…** and write the **Reason**, as in TR-01.  The report states it.
6. Click **Save** often.  The browser does not keep your project: the file you save is the
   only copy.

## 3 · Export

Open **Report Export**, fill the cover, signatories and equipment, pick the language, and
choose one:

- **Word (.docx)**, **HTML**, or **Test data summary (.xlsx)**: the file downloads.
- **Print to PDF**: the HTML report opens in a new tab and the print dialog appears.
  Choose "Save as PDF".  Allow pop-ups for the page if nothing opens.

The LaTeX PDF is made by the desktop app only.  Save the project, hand the file to a
colleague with the desktop workbench, and export the LaTeX PDF there.  The desktop opens
the same file unchanged.

## 4 · Checklist

- [ ] Opened the web address online and saw **Ready offline**.
- [ ] Reloaded with the network off and the app still started.
- [ ] Opened the project and checked the rated point and the edition.
- [ ] Filled in Test Points, MRT Log and NPSH.
- [ ] Read the Compliance and MRT Check rows, not only the pills.
- [ ] Wrote a Reason for every override.
- [ ] Saved the `.pumpflow` file.
- [ ] Exported the reports and opened them to check.

## 5 · What never leaves the machine

Everything.  The engine runs inside the browser.  Your project is read from your file and
held in memory, and reports are made in the browser and saved by the download.  After the
first load the app makes no network request.  The host only delivers the app files; it
never sees a project or a report.

See [`docs/web.md`](../web.md) for building, serving and troubleshooting.
