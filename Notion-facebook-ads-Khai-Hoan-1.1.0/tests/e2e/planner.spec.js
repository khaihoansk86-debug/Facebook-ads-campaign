const { test, expect } = require('@playwright/test');

async function openVideoFlow(page) {
  await page.locator('[data-campaign="ENG_BASE"]').click();
  await page.locator('[data-location="Trên quảng cáo của bạn"]').click();
  await page.locator('[data-adset="ENG_VIDEO_COLD"]').click();
  await page.locator('#audienceSelect').selectOption('AUD_BROAD_PHAN_THIET');
}

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#serverText')).toContainText('API Python đang chạy');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await expect(page.locator('#campaignList .choice').first()).toBeVisible();
});

test('lập hai bài với một cách chạy và hủy sửa an toàn', async ({ page }, testInfo) => {
  await page.locator('#linksInput').fill([
    'https://facebook.com/post-a',
    'https://fb.watch/video-b',
  ].join('\n'));
  await openVideoFlow(page);
  await expect(page.locator('#placementSelect')).toBeVisible();
  await expect(page.locator('#budgetSelect')).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('cau-hinh-planner-gon.png'), fullPage: true });
  await page.locator('#addFlowButton').click();

  await expect(page.locator('#summaryText')).toContainText('2 bài · 1 cách chạy · 2 mục');
  await expect(page.locator('.flow-card')).toContainText('Khách lạnh Phan Thiết');
  await expect(page.locator('.article-card')).toHaveCount(2);

  await page.getByRole('button', { name: 'Sửa' }).click();
  await expect(page.locator('#changeSelection')).toHaveText('Hủy chỉnh sửa');
  await page.locator('#changeSelection').click();
  await expect(page.locator('.flow-card')).toHaveCount(1);
  await expect(page.locator('#selectionStage')).toBeVisible();
  const floatingLayers = await page.evaluate(() => {
    const toast = document.querySelector('#toast').getBoundingClientRect();
    const actions = document.querySelector('#plannerActionbar').getBoundingClientRect();
    return { toastBottom: toast.bottom, actionTop: actions.top };
  });
  expect(floatingLayers.toastBottom).toBeLessThanOrEqual(floatingLayers.actionTop);
  await page.screenshot({ path: testInfo.outputPath('planner-hoan-chinh.png'), fullPage: true });
});

test('chặn ngân sách tùy chỉnh không hợp lệ ngay tại biểu mẫu', async ({ page }) => {
  await page.locator('#linksInput').fill('https://facebook.com/post-a');
  await openVideoFlow(page);
  await page.locator('#budgetAmount').fill('-1');
  await page.locator('#addFlowButton').click();

  await expect(page.locator('#toast')).toContainText('phải là một số lớn hơn 0');
  await expect(page.locator('#budgetAmount')).toBeFocused();
  await expect(page.locator('.flow-card')).toHaveCount(0);
});

test('cấu hình ngân sách và lịch chạy ngay trong Planner', async ({ page }) => {
  await page.locator('#linksInput').fill('https://facebook.com/post-a');
  await openVideoFlow(page);

  await expect(page.locator('#budgetAmount')).toHaveValue('800');
  await expect(page.locator('#startTime')).not.toHaveValue('');
  await expect(page.locator('#endTimeField')).toBeHidden();

  await page.locator('#hasEndTime').check();
  await expect(page.locator('#endTimeField')).toBeVisible();
  await page.locator('#hasEndTime').uncheck();
  await page.locator('#budgetType').selectOption('Ngân sách trọn đời');
  await expect(page.locator('#endTimeField')).toBeVisible();
  await expect(page.locator('#hasEndTime')).toBeDisabled();

  await page.locator('#addFlowButton').click();
  await expect(page.locator('#toast')).toContainText('trọn đời bắt buộc');
  await expect(page.locator('#endTime')).toBeFocused();

  await page.locator('#endTime').fill('2030-12-31T23:55');
  await page.locator('#addFlowButton').click();
  await expect(page.locator('.flow-card')).toContainText('800 PHP · Trọn đời');
});

test('tạo bundle đối tượng ở khu vực riêng', async ({ page }) => {
  let created;
  await page.route('**/api/presets/audiences', async route => {
    if (route.request().method() === 'POST') {
      created = route.request().postDataJSON();
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ok: true, preset: created }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, presets: created ? [created] : [] }) });
  });
  await page.getByRole('button', { name: 'Tệp đối tượng' }).click();
  await expect(page.locator('#libraryView')).toBeVisible();
  await page.locator('#newPresetButton').click();
  await page.locator('#presetCode').fill('AUD_KHACH_MOI');
  await page.locator('#presetName').fill('Khách mới Phan Thiết');
  await page.locator('[data-preset-field="Tuổi min"]').fill('18');
  await page.locator('[data-preset-field="Tuổi max"]').fill('45');
  await page.locator('#savePresetButton').click();
  await expect(page.locator('#presetList')).toContainText('Khách mới Phan Thiết');
  expect(created.notionValues['Tuổi min']).toBe(18);
  await page.getByRole('button', { name: 'Planner', exact: true }).click();
  await expect(page.locator('#plannerWorkspace')).toBeVisible();
});

test('thực thi đầy đủ thao tác tạo bản nháp và hiện liên kết Notion', async ({ page }) => {
  let submittedPayload;
  await page.route('**/api/planner/drafts', async route => {
    submittedPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        total: 1,
        created: 1,
        skipped: 0,
        failed: 0,
        results: [{
          position: 1,
          status: 'created',
          link: 'https://facebook.com/post-a',
          page_urls: ['https://notion.so/mock-page'],
        }],
      }),
    });
  });

  await page.locator('#linksInput').fill('https://facebook.com/post-a');
  await openVideoFlow(page);
  await page.locator('#addFlowButton').click();
  page.once('dialog', dialog => dialog.accept());
  await page.locator('#createDraftsButton').click();

  await expect(page.locator('#previewDialog')).toBeVisible();
  await expect(page.locator('#previewContent')).toContainText('1 mục đã tạo');
  await expect(page.getByRole('link', { name: 'Mở trang Notion 1' })).toHaveAttribute('href', 'https://notion.so/mock-page');
  expect(submittedPayload.links).toEqual(['https://facebook.com/post-a']);
  expect(submittedPayload.flows).toHaveLength(1);
  expect(submittedPayload.flows[0].audience_codes).toEqual(['AUD_BROAD_PHAN_THIET']);
  expect(submittedPayload.flows[0].custom_budget_values).toEqual({ 'Ngân sách/ngày': '800' });
  expect(submittedPayload.flows[0].start_time).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  expect(submittedPayload.flows[0].end_time).toBeNull();
});

test('duyệt xuất chỉ hiển thị dữ liệu đã hoàn thành', async ({ page }, testInfo) => {
  let exportedPageIds;
  await page.route('**/api/export/candidates', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true,
      candidates: [{
        id: 'page-test',
        name: 'Quảng cáo thử nghiệm',
        status: 'Hoàn thành',
        campaign: 'Lượt tương tác',
        adset: 'Tối đa hóa lượt xem video',
        audience: 'Khách lạnh Phan Thiết',
        budget: '800',
        post_url: 'https://facebook.com/post-a',
        url: 'https://notion.so/page-test',
      }],
    }),
  }));
  await page.route('**/api/export', async route => {
    exportedPageIds = route.request().postDataJSON().page_ids;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        count: 1,
        file_name: 'facebook_test.csv',
        download_url: '/api/exports/facebook_test.csv',
        sync_warning: '',
      }),
    });
  });

  await page.locator('#reviewExportButton').click();
  await expect(page.locator('.candidate-card')).toContainText('Quảng cáo thử nghiệm');
  await expect(page.locator('.candidate-status')).toHaveText('Hoàn thành');
  await page.locator('[data-candidate-id="page-test"]').check();
  await expect(page.locator('#exportSelectedButton')).toHaveText('Xuất 1 bài đã chọn');
  page.once('dialog', dialog => dialog.accept());
  await page.locator('#exportSelectedButton').click();
  await expect(page.locator('#exportResult')).toContainText('Đã xuất 1 quảng cáo');
  await expect(page.locator('#exportResult a')).toHaveAttribute('href', '/api/exports/facebook_test.csv');
  expect(exportedPageIds).toEqual(['page-test']);
  await page.screenshot({ path: testInfo.outputPath('duyet-xuat-hoan-chinh.png'), fullPage: true });
  await page.locator('#backToPlannerButton').click();
  await expect(page.locator('#plannerWorkspace')).toBeVisible();
});

test('không tràn ngang ở kích thước đang kiểm thử', async ({ page }) => {
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});
