"""Render the exact meshes inside the customer download ZIP. Never regenerate geometry."""
from pathlib import Path
import hashlib,json,zipfile,tempfile
import vtk
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
archive=ROOT/'public/downloads/3d-print/LINK_COMMANDER_ENCLOSURE_A1.zip'
ren=vtk.vtkRenderer();ren.SetBackground(.961,.941,.898)
manifest={'method':'VTK rendering of the exact downloadable STL triangle meshes. Translation for plate placement only; no geometry reconstruction or generative image editing.','archive':str(archive.relative_to(ROOT)),'archiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'meshes':{}}
def add(poly,color,position=(0,0,0)):
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(poly)
 actor=vtk.vtkActor();actor.SetMapper(mapper);actor.SetPosition(*position)
 p=actor.GetProperty();p.SetColor(*color);p.SetAmbient(.22);p.SetDiffuse(.78);p.SetSpecular(.22);p.SetSpecularPower(30);p.SetInterpolationToPhong()
 ren.AddActor(actor);return actor
with tempfile.TemporaryDirectory(prefix='roddy-stl-render-') as tmp:
 with zipfile.ZipFile(archive) as z:
  for name,color,pos in [('BASE_print',(.16,.18,.20),(7,78,0)),('LID_print',(.83,.79,.69),(135,78,0))]:
   member='LINK_COMMANDER_ENCLOSURE_A/print/'+name+'.stl';data=z.read(member);path=Path(tmp)/(name+'.stl');path.write_bytes(data)
   reader=vtk.vtkSTLReader();reader.SetFileName(str(path));reader.Update();poly=reader.GetOutput()
   manifest['meshes'][member]={'sha256':hashlib.sha256(data).hexdigest(),'triangles':poly.GetNumberOfCells(),'translationMm':pos}
   normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly);normals.SetFeatureAngle(45);normals.Update();add(normals.GetOutput(),color,pos)
# A visual print plate. Only the two case pieces are downloadable geometry.
plate=vtk.vtkCubeSource();plate.SetBounds(0,256,0,256,-3,-.12);plate.Update();add(plate.GetOutput(),(.22,.235,.24))
for i in range(1,26):
 for a,b in [((i*10,0,-.08),(i*10,256,-.08)),((0,i*10,-.08),(256,i*10,-.08))]:
  line=vtk.vtkLineSource();line.SetPoint1(*a);line.SetPoint2(*b);line.Update();act=add(line.GetOutput(),(.35,.36,.35));act.GetProperty().SetLineWidth(.5)
# Warm key and broad camera fill reveal real snap latches and lid guard.
for pos,power in [((-100,-200,350),.8),((250,80,300),.55)]:
 light=vtk.vtkLight();light.SetPosition(*pos);light.SetFocalPoint(128,125,0);light.SetIntensity(power);ren.AddLight(light)
cam=ren.GetActiveCamera();cam.SetFocalPoint(128,125,0);cam.SetPosition(240,-260,330);cam.SetViewUp(0,0,1);cam.ParallelProjectionOn();cam.SetParallelScale(118)
win=vtk.vtkEGLRenderWindow();win.SetOffScreenRendering(1);win.SetSize(1800,1160);win.SetMultiSamples(8);win.AddRenderer(ren);win.Render()
shot=vtk.vtkWindowToImageFilter();shot.SetInput(win);shot.ReadFrontBufferOff();shot.Update();writer=vtk.vtkPNGWriter();writer.SetFileName(str(OUT/'native/lc-stl-exact.png'));writer.SetInputConnection(shot.GetOutputPort());writer.Write();win.Finalize()
(OUT/'native/lc-stl-provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Rendered exact downloadable Link Commander STL meshes.')
