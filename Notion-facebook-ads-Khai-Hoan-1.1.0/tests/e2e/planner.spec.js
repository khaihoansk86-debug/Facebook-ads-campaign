const { test, expect } = require('@playwright/test');

async function openVideoFlow(page) {
  await page.locator('[data-campaign="ENG_BASE"]').click();
  await page.locator('[data-location="Trên quảng cáo của bạn"]').click();
  await page.locator('[data-adset="ENG_VIDEO_COLD"]').click();
  await page.locator('#audienceSelect').selectOption('AUD_BROAD_PHAN_THIET');
  if (!await page.locator('#budgetAmount').inputValue()) {
    await page.locator('#budgetAmount').fill('10');
  }
}

test.beforeEach(async ({ page }) => {
  await page.route('**/api/meta/status**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true,
      configured: true,
      connected: true,
      account: { id: 'act_test', name: 'Tài khoản thử', currency: 'USD' },
    }),
  }));
  await page.route('**/api/meta/creative-previews', async route => {
    const payload = route.request().postDataJSON();
    const previews = (payload.links || []).map(link => link.includes('creative-preview-test')
      ? {
          link,
          status: 'ready',
          page_name: 'Khải Hoàn Clinic',
          message: 'Creative mẫu hiển thị ngay trong Planner',
          media_type: 'photo',
          thumbnail_url: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="64" height="64"%3E%3Crect width="64" height="64" fill="%231877f2"/%3E%3C/svg%3E',
          permalink_url: link,
        }
      : {
          link,
          status: 'unavailable',
          message: '',
          page_name: '',
          media_type: '',
          thumbnail_url: '',
          permalink_url: link,
        });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        previews,
        summary: {
          total: previews.length,
          ready: previews.filter(item => item.status === 'ready').length,
          unavailable: previews.filter(item => item.status !== 'ready').length,
        },
      }),
    });
  });
  await page.goto('/');
  await expect(page.locator('#serverText')).toContainText('Backend');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await expect(page.locator('#campaignList .choice').first()).toBeVisible();
});

test('hiển thị nhanh creative của bài viết nhưng không chặn link không đọc được', async ({ page }) => {
  await page.locator('#linksInput').fill([
    'https://facebook.com/page/posts/creative-preview-test',
    'https://facebook.com/page/posts/no-access',
  ].join('\n'));

  await expect(page.locator('.creative-preview')).toHaveCount(1);
  await expect(page.locator('.creative-preview')).toContainText('Khải Hoàn Clinic');
  await expect(page.locator('.creative-preview')).toContainText('Creative mẫu hiển thị ngay trong Planner');
  await expect(page.locator('.creative-preview img')).toHaveAttribute('loading', 'lazy');
  await expect(page.locator('.creative-preview-status.unavailable')).toHaveCount(1);
  await expect(page.locator('.creative-preview-status.unavailable')).toContainText('vẫn có thể lập kế hoạch');
  await expect(page.locator('#selectedLinkCount')).toHaveText('2/2 bài đang chọn');
  const previewLayout = await page.locator('.creative-preview').evaluate(element => {
    const image = element.querySelector('img').getBoundingClientRect();
    const copy = element.querySelector('.creative-preview-copy').getBoundingClientRect();
    const card = element.closest('.link-select-card').getBoundingClientRect();
    return {
      separated: image.right <= copy.left,
      insideCard: copy.right <= card.right && image.bottom <= card.bottom,
    };
  });
  expect(previewLayout.separated).toBeTruthy();
  expect(previewLayout.insideCard).toBeTruthy();
});

test('imports Page posts by date without duplicating existing links', async ({ page }) => {
  const firstLink = 'https://facebook.com/page/posts/creative-preview-test-1';
  const secondLink = 'https://facebook.com/page/posts/creative-preview-test-2';
  await page.route('**/api/meta/page-posts?**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true,
      page_id: '111',
      page_name: 'Khai Hoan Clinic',
      since: '2026-07-01',
      until: '2026-07-07',
      posts: [
        {
          link: firstLink,
          permalink_url: firstLink,
          object_story_id: '111_1',
          status: 'ready',
          page_name: 'Khai Hoan Clinic',
          message: 'Existing Planner post',
          created_time: '2026-07-07T08:00:00+0000',
          media_type: 'photo',
          thumbnail_url: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="72" height="72"%3E%3Crect width="72" height="72" fill="%231877f2"/%3E%3C/svg%3E',
        },
        {
          link: secondLink,
          permalink_url: secondLink,
          object_story_id: '111_2',
          status: 'ready',
          page_name: 'Khai Hoan Clinic',
          message: 'New post selected by date',
          created_time: '2026-07-06T08:00:00+0000',
          media_type: 'photo',
          thumbnail_url: '',
        },
      ],
      summary: { total: 2, truncated: false, max_posts: 500 },
    }),
  }));
  await page.locator('#linksInput').fill(firstLink);
  await page.locator('#openPagePostsButton').click();
  await expect(page.locator('#pagePostsDialog')).toHaveAttribute('open', '');
  await page.locator('#pagePostsSince').fill('2026-07-01');
  await page.locator('#pagePostsUntil').fill('2026-07-07');
  await page.locator('#loadPagePostsButton').click();

  await expect(page.locator('.page-post-card')).toHaveCount(2);
  await expect(page.locator('.page-post-card.already-added')).toHaveCount(1);
  await expect(page.locator('#pagePostsStatus')).toContainText('1 bài đang chọn');
  await page.locator('#addPagePostsButton').click();

  await expect(page.locator('#linksInput')).toHaveValue(`${firstLink}\n${secondLink}`);
  await expect(page.locator('.link-select-card')).toHaveCount(2);
  await expect(page.locator('.creative-preview')).toHaveCount(2);
});

test('có thể đóng đăng nhập người duyệt sau khi đã nhập dữ liệu', async ({ page }) => {
  await page.locator('[data-app-view="reviews"]').click();
  await page.locator('#approverLoginButton').click();
  await page.locator('#approverName').fill('IT Test');
  await page.locator('#approverKey').fill('khong-dang-nhap');

  await page.locator('#approverDialog [aria-label="Đóng cửa sổ đăng nhập"]').click();

  await expect(page.locator('#approverDialog')).not.toHaveAttribute('open', '');
  await expect(page.locator('#approverKey')).toHaveValue('');

  await page.locator('#approverLoginButton').click();
  await page.keyboard.press('Escape');
  await expect(page.locator('#approverDialog')).not.toHaveAttribute('open', '');
});

test('lập hai bài với một cách chạy và hủy sửa an toàn', async ({ page }, testInfo) => {
  await page.locator('#linksInput').fill([
    'https://facebook.com/post-a',
    'https://fb.watch/video-b',
  ].join('\n'));
  await openVideoFlow(page);
  await expect(page.locator('#placementSelect')).toBeVisible();
  await expect(page.locator('#budgetSelect')).toBeVisible();
  await expect(page.locator('#placementSelect')).toHaveValue('PLC_FB_FEED_REELS_SEARCH_MOBILE');
  await expect(page.locator('#budgetCurrency')).toHaveText('USD');
  await page.screenshot({ path: testInfo.outputPath('cau-hinh-planner-gon.png'), fullPage: true });
  await page.locator('#addFlowButton').click();

  await expect(page.locator('#summaryText')).toContainText('2 bài · 1 flow · 2 mục');
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

test('áp dụng tuần tự một flow cho nhiều link rồi thêm flow riêng cho một link', async ({ page }) => {
  await page.locator('#linksInput').fill([
    'https://facebook.com/post-a',
    'https://facebook.com/post-b',
  ].join('\n'));
  await expect(page.locator('#selectedLinkCount')).toHaveText('2/2 bài đang chọn');

  await openVideoFlow(page);
  await page.locator('#addFlowButton').click();
  await expect(page.locator('.flow-card')).toHaveCount(1);
  await expect(page.locator('.flow-card').first()).toContainText('2 bài');

  await page.locator('[data-plan-link-index="1"]').uncheck();
  await expect(page.locator('#selectedLinkCount')).toHaveText('1/2 bài đang chọn');
  await page.locator('[data-campaign="AWARENESS_BASE"]').click();
  await page.locator('#locationList [data-location]').first().click();
  await page.locator('[data-adset="AWR_REACH"]').click();
  await page.locator('#audienceSelect').selectOption('AUD_BROAD_PHAN_THIET');
  await page.locator('#budgetAmount').fill('10');
  await page.locator('#addFlowButton').click();

  await expect(page.locator('.flow-card')).toHaveCount(2);
  await expect(page.locator('#summaryText')).toContainText('2 bài · 2 flow · 3 mục');
  await expect(page.locator('.article-card').nth(0).locator('.article-flow')).toHaveCount(2);
  await expect(page.locator('.article-card').nth(1).locator('.article-flow')).toHaveCount(1);

  await page.locator('#previewButton').click();
  await expect(page.locator('#previewContent')).toContainText('2 campaign · 2 nhóm quảng cáo · 3 quảng cáo');
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

  await expect(page.locator('#budgetAmount')).toHaveValue('10');
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
  await expect(page.locator('.flow-card')).toContainText('10 USD · Trọn đời');
});

test('tạo tệp đối tượng bằng lựa chọn Kiểm soát và Gợi ý như Meta', async ({ page }, testInfo) => {
  let created;
  await page.setViewportSize({ width: 760, height: 820 });
  await page.route('**/api/meta/audiences', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true,
      account_id: 'act_1',
      audiences: [
        { id: '120246010546010657', name: 'Đã tương tác trang 365 ngày', kind: 'custom', subtype: 'ENGAGEMENT' },
        { id: '120299999999999999', name: 'Tương tự khách tốt nhất 1%', kind: 'lookalike', subtype: 'LOOKALIKE' },
      ],
    }),
  }));
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
  await expect(page.getByRole('button', { name: /Tệp rộng/ })).toHaveClass(/selected/);
  await expect(page.getByRole('button', { name: /Đối tượng tùy chỉnh/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Đối tượng tương tự/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Kiểm soát đối tượng' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Gợi ý đối tượng' })).toBeVisible();
  const audienceLayout = await page.locator('.audience-composer').evaluate(composer => {
    const sections = [...composer.querySelectorAll('.audience-section')];
    const firstNumber = sections[0].querySelector('.audience-section-number').getBoundingClientRect();
    const firstTitle = sections[0].querySelector('h3').getBoundingClientRect();
    const editor = composer.closest('.preset-editor').getBoundingClientRect();
    return {
      numberAligned: Math.abs(firstNumber.top - firstTitle.top) <= 6,
      sectionsInsideEditor: sections.every(section => {
        const box = section.getBoundingClientRect();
        return box.left >= editor.left && box.right <= editor.right;
      }),
      sectionsSeparated: sections[1].getBoundingClientRect().top >= sections[0].getBoundingClientRect().bottom,
      noHorizontalOverflow: composer.scrollWidth <= composer.clientWidth,
    };
  });
  expect(audienceLayout).toEqual({
    numberAligned: true,
    sectionsInsideEditor: true,
    sectionsSeparated: true,
    noHorizontalOverflow: true,
  });
  await page.screenshot({ path: testInfo.outputPath('tep-doi-tuong-760px.png'), fullPage: true });
  await expect(page.locator('#presetCodeField')).toBeHidden();
  await page.locator('#presetName').fill('Khách mới Phan Thiết');
  await page.locator('[data-preset-field="Vị trí địa lý"]').selectOption('Phan Thiet, Bình Thuận Province, Vietnam +25km');
  await page.locator('[data-preset-field="Tuổi kiểm soát min"]').selectOption('18');
  await page.locator('[data-preset-field="Tuổi min"]').selectOption('22');
  await page.locator('[data-preset-field="Tuổi max"]').selectOption('45');
  await page.getByRole('button', { name: 'Nữ', exact: true }).click();
  await expect(page.locator('[data-preset-field="Loại trừ đối tượng"]')).toHaveValue('');
  await expect(page.locator('[data-preset-field="Nhắm mục tiêu chi tiết"]')).toHaveValue('');
  await page.locator('#savePresetButton').click();
  await expect(page.locator('#presetList')).toContainText('Khách mới Phan Thiết');
  expect(created.code).toMatch(/^AUD_/);
  expect(created.notionValues['Tuổi min']).toBe(22);
  expect(created.notionValues['Tuổi max']).toBe(45);
  expect(created.notionValues['Giới tính']).toBe('Nữ');
  expect(created.notionValues).not.toHaveProperty('Loại trừ đối tượng');
  expect(created.notionValues).not.toHaveProperty('Nhắm mục tiêu chi tiết');
  await page.getByRole('button', { name: 'Planner', exact: true }).click();
  await expect(page.locator('#plannerWorkspace')).toBeVisible();
});

test('tệp đối tượng tùy chỉnh và tương tự chọn trực tiếp tài sản Meta', async ({ page }) => {
  const saved = [];
  await page.route('**/api/meta/audiences', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true,
      account_id: 'act_1',
      audiences: [
        { id: '120246010546010657', name: 'Đã tương tác trang 365 ngày', kind: 'custom', subtype: 'ENGAGEMENT' },
        { id: '120299999999999999', name: 'Tương tự khách tốt nhất 1%', kind: 'lookalike', subtype: 'LOOKALIKE' },
      ],
    }),
  }));
  await page.route('**/api/presets/audiences', async route => {
    if (route.request().method() === 'POST') {
      saved.push(route.request().postDataJSON());
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ok: true, preset: saved.at(-1) }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, presets: saved }) });
  });

  await page.getByRole('button', { name: 'Tệp đối tượng' }).click();
  await page.locator('#newPresetButton').click();
  await page.getByRole('button', { name: /Đối tượng tùy chỉnh/ }).click();
  await page.locator('[data-preset-field="Đối tượng tuỳ chỉnh"]').selectOption({ label: 'Đã tương tác trang 365 ngày' });
  await page.locator('#savePresetButton').click();
  expect(saved[0].notionValues['Loại tệp đối tượng']).toBe('Đối tượng tùy chỉnh');
  expect(saved[0].notionValues['Đối tượng tuỳ chỉnh']).toContain('120246010546010657');

  await page.locator('#newPresetButton').click();
  await page.getByRole('button', { name: /Đối tượng tương tự/ }).click();
  await page.locator('[data-preset-field="Đối tượng tương tự"]').selectOption({ label: 'Tương tự khách tốt nhất 1%' });
  await page.locator('#savePresetButton').click();
  expect(saved[1].notionValues['Loại tệp đối tượng']).toBe('Đối tượng tương tự');
  expect(saved[1].notionValues['Đối tượng tương tự']).toContain('120299999999999999');
});

test('tạo vị trí quảng cáo bằng lựa chọn thiết bị nền tảng và placement như Meta', async ({ page }, testInfo) => {
  let created;
  await page.setViewportSize({ width: 760, height: 820 });
  await page.route('**/api/presets/placements', async route => {
    if (route.request().method() === 'POST') {
      created = route.request().postDataJSON();
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ok: true, preset: created }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, presets: created ? [created] : [] }) });
  });

  await page.getByRole('button', { name: 'Vị trí quảng cáo' }).click();
  await page.locator('#newPresetButton').click();
  await expect(page.getByRole('heading', { name: 'Thiết bị' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Nền tảng' })).toBeVisible();
  await expect(page.locator('#presetFields').getByRole('heading', { name: 'Vị trí quảng cáo', exact: true })).toBeVisible();
  await expect(page.locator('#presetCodeField')).toBeHidden();
  await expect(page.locator('[data-preset-field="Thiết bị"]')).toHaveValue('Di động');
  await expect(page.locator('[data-preset-field="Nền tảng quảng cáo"]')).toHaveValue('Facebook');
  await expect(page.locator('[data-preset-field="Vị trí Facebook"]')).toHaveValue('feed, facebook_reels, search');
  await expect(page.locator('[data-placement-group="instagram"]')).toBeHidden();

  await page.getByRole('button', { name: 'Tất cả', exact: true }).click();
  await page.locator('[data-placement-platform="instagram"]').check();
  await expect(page.locator('[data-placement-group="instagram"]')).toBeVisible();
  await page.locator('[data-placement-group="instagram"] [value="story"]').uncheck();
  await page.screenshot({ path: testInfo.outputPath('vi-tri-quang-cao-760px.png'), fullPage: true });
  await page.locator('#savePresetButton').click();

  await expect(page.locator('#presetList')).toContainText('Facebook + Instagram · Tất cả');
  expect(created.code).toMatch(/^PLC_/);
  expect(created.notionValues['Thiết bị']).toBe('Tất cả');
  expect(created.notionValues['Nền tảng quảng cáo']).toBe('Facebook + Instagram');
  expect(created.notionValues['Vị trí Facebook']).toBe('feed, facebook_reels, search');
  expect(created.notionValues['Vị trí Instagram']).toBe('stream, reels');
  expect(created.notionValues).not.toHaveProperty('Vị trí Messenger');
});

test('Content gửi kế hoạch và xem cây đang chờ duyệt', async ({ page }, testInfo) => {
  let submittedPayload;
  const review = {
    id: 'review-1',
    status: 'PENDING_REVIEW',
    submitted_by: 'Content',
    submitted_at: '2026-07-27T08:00:00+00:00',
    reviewer_note: '',
    summary: { campaigns_count: 1, adsets_count: 1, ads_count: 1 },
    tree: [{
      code: 'ENG_BASE',
      name: 'Tương tác',
      adsets: [{
        position: 1,
        code: 'ENG_VIDEO_COLD',
        name: 'Xem video',
        conversion_location: 'Trên quảng cáo của bạn',
        performance_goal: 'Tối đa hóa lượt xem video',
        audiences: ['Khách lạnh Phan Thiết'],
        custom_budget_values: { 'Ngân sách/ngày': '800' },
        budget: '800/ngày',
        placement: 'Facebook mobile',
        start_time: '2026-07-27T15:00+07:00',
        end_time: null,
        ads: [{ position: 1, name: 'Bài 1', link: 'https://facebook.com/post-a' }],
      }],
    }],
  };
  await page.route('**/api/reviews**', async route => {
    const url = new URL(route.request().url());
    if (route.request().method() === 'POST' && url.pathname === '/api/reviews') {
      submittedPayload = route.request().postDataJSON();
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ok: true, review, deduplicated: false }) });
      return;
    }
    if (url.pathname === '/api/reviews') {
      const { tree, ...summary } = review;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, reviews: [summary] }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, review }) });
  });

  await page.locator('#linksInput').fill('https://facebook.com/post-a');
  await openVideoFlow(page);
  await page.locator('#addFlowButton').click();
  await page.locator('#previewButton').click();
  await expect(page.locator('#previewContent')).toContainText('IT/Ads Operator');
  await page.locator('#closeDialog').click();
  await page.locator('#createDraftsButton').click();

  await expect(page.locator('#reviewView')).toBeVisible();
  await expect(page.locator('#reviewDetailStatus')).toHaveText('Chờ duyệt');
  await expect(page.locator('#reviewTree')).toContainText('Campaign · Tương tác');
  await expect(page.locator('#reviewTree')).toContainText('Nhóm quảng cáo 1 · Xem video');
  await expect(page.locator('#reviewTree')).toContainText('Bài 1');
  await page.screenshot({ path: testInfo.outputPath('duyet-ke-hoach.png'), fullPage: true });
  expect(submittedPayload.links).toEqual(['https://facebook.com/post-a']);
  expect(submittedPayload.flows).toHaveLength(1);
  expect(submittedPayload.flows[0].audience_codes).toEqual(['AUD_BROAD_PHAN_THIET']);
  expect(submittedPayload.flows[0].custom_budget_values).toEqual({ 'Ngân sách/ngày': '10' });
  expect(submittedPayload.flows[0].start_time).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  expect(submittedPayload.flows[0].end_time).toBeNull();
});

test('IT duyệt rồi tạo PAUSED qua phiên có CSRF', async ({ page }) => {
  let currentStatus = 'PENDING_REVIEW';
  let csrfHeader;
  const fullReview = () => ({
    id: 'review-it',
    status: currentStatus,
    submitted_by: 'Content',
    submitted_at: '2026-07-27T08:00:00+00:00',
    reviewer_note: '',
    summary: { campaigns_count: 1, adsets_count: 1, ads_count: 1 },
    tree: [{
      code: 'ENG_BASE',
      name: 'Tương tác',
      adsets: [{
        position: 1, code: 'ENG_VIDEO_COLD', name: 'Xem video',
        conversion_location: 'Trên quảng cáo của bạn', performance_goal: 'Tối đa hóa lượt xem video',
        audiences: ['Khách lạnh'], custom_budget_values: { 'Ngân sách/ngày': '800' },
        placement: 'Facebook mobile', start_time: null, end_time: null,
        ads: [{ position: 1, name: 'Bài 1', link: 'https://facebook.com/post-a' }],
      }],
    }],
  });
  await page.route('**/api/auth/me', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ ok: true, configured: true, authenticated: false, role: 'content', csrf_token: null }),
  }));
  await page.route('**/api/auth/approver', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ ok: true, authenticated: true, role: 'approver', reviewer: 'IT Test', csrf_token: 'csrf-test' }),
  }));
  await page.route('**/api/reviews**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST' && path.endsWith('/approve')) {
      csrfHeader = await request.headerValue('x-csrf-token');
      currentStatus = 'APPROVED';
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, review: fullReview() }) });
      return;
    }
    if (request.method() === 'POST' && path.endsWith('/publish')) {
      csrfHeader = await request.headerValue('x-csrf-token');
      currentStatus = 'META_CREATED';
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, review: fullReview() }) });
      return;
    }
    if (path === '/api/reviews') {
      const { tree, ...summary } = fullReview();
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, reviews: [summary] }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, review: fullReview() }) });
  });

  await page.getByRole('button', { name: 'Duyệt kế hoạch' }).click();
  await page.locator('[data-review-id="review-it"]').click();
  await expect(page.locator('#reviewActions')).toBeHidden();
  await page.locator('#approverLoginButton').click();
  await page.locator('#approverName').fill('IT Test');
  await page.locator('#approverKey').fill('secret');
  await page.locator('#approverSubmitButton').click();
  await expect(page.locator('#approveReviewButton')).toBeVisible();
  await page.locator('#approveReviewButton').click();
  await expect(page.locator('#reviewDetailStatus')).toHaveText('Đã duyệt');
  await expect(page.locator('#publishReviewButton')).toBeVisible();
  page.once('dialog', dialog => dialog.accept());
  await page.locator('#publishReviewButton').click();
  await expect(page.locator('#reviewDetailStatus')).toHaveText('Đã tạo PAUSED');
  expect(csrfHeader).toBe('csrf-test');
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
