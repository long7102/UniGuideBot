// Entire export stays in this browser; no profile is posted to an export API.
const exportButton=document.querySelector('#export-profile');
async function fontBase64(url){const response=await fetch(url);if(!response.ok)throw Error('Chưa tải được phông PDF.');const bytes=new Uint8Array(await response.arrayBuffer());let value='';for(let i=0;i<bytes.length;i+=8192)value+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(value);}
async function createProfilePdf(profile,recommendation){
 if(!window.jspdf?.jsPDF)throw Error('Thư viện PDF chưa sẵn sàng. Hãy tải lại trang.');
 const doc=new window.jspdf.jsPDF({unit:'mm',format:'a4',compress:true});
 const [regular,bold]=await Promise.all([fontBase64('/static/fonts/NotoSans-Regular.ttf'),fontBase64('/static/fonts/NotoSans-Bold.ttf')]);
 doc.addFileToVFS('NotoSans-Regular.ttf',regular);doc.addFont('NotoSans-Regular.ttf','NotoSans','normal');doc.addFileToVFS('NotoSans-Bold.ttf',bold);doc.addFont('NotoSans-Bold.ttf','NotoSans','bold');
 const margin=21,width=168,bottom=274;let y=24;
 function newPage(){doc.addPage();y=24;}
 function write(value,{size=10,bold=false,color=[51,63,85],gap=4}={}){doc.setFont('NotoSans',bold?'bold':'normal');doc.setFontSize(size);doc.setTextColor(...color);for(const paragraph of String(value||'').split('\n')){const lines=doc.splitTextToSize(paragraph||' ',width);for(const line of lines){if(y+size*.48>bottom)newPage();doc.text(line,margin,y);y+=size*.48;}y+=gap/2;}y+=gap/2;}
 function title(value){if(y>245)newPage();y+=5;write(value,{size:13,bold:true,color:[102,84,217],gap:5});}
 doc.setFillColor(102,84,217);doc.rect(0,0,210,5,'F');write('UNIGUIDEBOT',{size:10,bold:true,color:[102,84,217],gap:7});write('Hồ sơ & lộ trình của bạn',{size:23,bold:true,color:[32,42,69],gap:7});write('Bản xuất ngày '+new Date().toLocaleDateString('vi-VN'),{size:9,color:[115,127,149],gap:8});
 title('01  Hiểu mình');const labels={interests:'Sở thích',strengths:'Thế mạnh',subjects:'Môn học / kỹ năng',score:'Điểm và phương thức dự kiến',budget:'Ngân sách',region:'Khu vực',field:'Nhóm ngành',goals:'Mục tiêu nghề nghiệp'};
 for(const [key,label] of Object.entries(labels)){if(!profile[key])continue;let value=profile[key];if(key==='field')value=fieldLabels[value]||value;if(key==='region')value={bac:'Miền Bắc',trung:'Miền Trung',nam:'Miền Nam'}[value]||value;write(label,{bold:true,size:9,gap:1});write(value,{gap:5});}
 title('02  Định hướng & lộ trình');
 if(recommendation?.ai_powered)write(recommendation.message);else write('Chưa có lộ trình AI được tạo cho hồ sơ này. Sau khi nhận tư vấn, bạn có thể xuất lại để bổ sung kế hoạch 90 ngày.');
 if(recommendation?.universities?.length){title('03  Các trường để tìm hiểu');for(const school of recommendation.universities){write(school.name,{bold:true,size:10,gap:1});write(school.city+(school.admission_code?' · Mã tuyển sinh '+school.admission_code:''),{size:9,gap:1});if(school.website)write(school.website,{size:8,color:[102,84,217],gap:5});}}
 if(recommendation?.sources?.length){title('Nguồn tham khảo');for(const source of recommendation.sources)write('['+source.id+'] '+source.title+'\n'+source.url,{size:8,gap:4});}
 title('Ghi chú');write('Gợi ý định hướng không bảo đảm trúng tuyển hay việc làm. Đối chiếu nguồn chính thức, năm dữ liệu, ngành và phương thức xét tuyển. Hồ sơ được xuất trên trình duyệt của bạn.',{size:8,color:[115,127,149]});
 for(let number=1;number<=doc.getNumberOfPages();number++){doc.setPage(number);doc.setDrawColor(229,232,241);doc.line(21,283,189,283);doc.setFont('NotoSans','normal');doc.setFontSize(8);doc.setTextColor(115,127,149);doc.text('UniGuideBot · Kế hoạch cá nhân',21,290);doc.text(number+' / '+doc.getNumberOfPages(),189,290,{align:'right'});}
 return doc;
}
exportButton.addEventListener('click',async()=>{exportButton.disabled=true;$('#export-status').textContent='Đang tạo PDF…';try{const profile=currentProfile();if(!Object.values(profile).some(Boolean))throw Error('Hãy nhập hồ sơ trước khi xuất.');const matching=lastRecommendation&&profileKeys.every(key=>(lastRecommendation.profile_snapshot?.[key]||'')===(profile[key]||''));const pdf=await createProfilePdf(profile,matching?lastRecommendation:null);pdf.save('UniGuideBot-Ho-so-va-lo-trinh.pdf');$('#export-status').textContent='PDF đã được tạo.';}catch(error){$('#export-status').textContent=error.message;}finally{exportButton.disabled=false;}});
